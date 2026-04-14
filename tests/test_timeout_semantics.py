"""
超时语义统一性测试

测试目标：
1. 验证 TimeoutConfig 配置类
2. 验证单命令超时和批量超时的语义一致性
3. 验证日志记录完整性
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
import time

from gateflow.config import TimeoutConfig, DEFAULT_TIMEOUT_CONFIG
from gateflow.engine import EngineManager, execute_tcl_batch
from gateflow.vivado.tcp_client import VivadoTcpClient, TcpConfig, TclResponse


class TestTimeoutConfig:
    """测试 TimeoutConfig 配置类"""
    
    def test_default_values(self):
        """测试默认值"""
        config = TimeoutConfig()
        assert config.single_command == 60.0
        assert config.batch_total == 3600.0
        assert config.connect == 10.0
        assert config.idle == 300.0
    
    def test_custom_values(self):
        """测试自定义值"""
        config = TimeoutConfig(
            single_command=60.0,
            batch_total=7200.0,
            connect=15.0,
            idle=600.0,
        )
        assert config.single_command == 60.0
        assert config.batch_total == 7200.0
        assert config.connect == 15.0
        assert config.idle == 600.0
    
    def test_validation_positive_values(self):
        """测试验证：必须为正值"""
        with pytest.raises(ValueError, match="single_command 必须大于 0"):
            TimeoutConfig(single_command=0)
        
        with pytest.raises(ValueError, match="batch_total 必须大于 0"):
            TimeoutConfig(batch_total=-10)
    
    def test_warning_batch_less_than_single(self):
        """测试警告：批量超时小于单命令超时"""
        with pytest.warns(UserWarning, match="batch_total.*小于.*single_command"):
            TimeoutConfig(
                single_command=100.0,
                batch_total=50.0,
            )
    
    def test_default_instance(self):
        """测试默认实例"""
        assert DEFAULT_TIMEOUT_CONFIG.single_command == 60.0
        assert DEFAULT_TIMEOUT_CONFIG.batch_total == 3600.0


class TestEngineManagerTimeout:
    """测试 EngineManager 的超时行为"""
    
    @pytest.fixture
    def engine_manager(self):
        """创建 EngineManager 实例"""
        manager = EngineManager()
        # 重置单例状态
        manager._initialized = False
        manager._tcp_client = None
        manager._tcl_engine = None
        return manager
    
    @pytest.mark.asyncio
    async def test_execute_batch_uses_default_timeout(self, engine_manager):
        """测试批量执行使用默认超时配置"""
        # Mock TCP 客户端
        mock_client = Mock(spec=VivadoTcpClient)
        mock_client.is_connected = True
        mock_client.execute_tcl = AsyncMock(return_value=TclResponse(
            success=True,
            result="OK",
            execution_time=0.1,
        ))
        
        engine_manager._tcp_client = mock_client
        engine_manager._mode = "tcp"
        engine_manager._initialized = True
        
        # 执行批量命令，不指定超时
        commands = ["puts Hello", "puts World"]
        results = await engine_manager.execute_batch(commands)
        
        # 验证每个命令都被执行
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_execute_batch_total_timeout(self, engine_manager):
        """测试批量执行总超时"""
        # Mock TCP 客户端，模拟慢速响应
        async def slow_execute(command, timeout, auto_reconnect=True):
            await asyncio.sleep(0.2)  # 模拟慢速执行
            return TclResponse(success=True, result="OK", execution_time=0.2)
        
        mock_client = Mock(spec=VivadoTcpClient)
        mock_client.is_connected = True
        mock_client.execute_tcl = slow_execute
        
        engine_manager._tcp_client = mock_client
        engine_manager._mode = "tcp"
        engine_manager._initialized = True
        
        # 设置很短的总超时
        commands = ["cmd1", "cmd2", "cmd3", "cmd4", "cmd5"]
        results = await engine_manager.execute_batch(
            commands,
            timeout=0.5,  # 总超时 0.5 秒
            per_command_timeout=1.0,  # 单命令超时 1 秒
        )
        
        # 验证部分命令因总超时而未执行
        assert len(results) == 5
        # 前几个命令应该成功
        success_count = sum(1 for r in results if r.success)
        # 后面的命令应该因超时失败
        timeout_count = sum(1 for r in results if not r.success and r.error and "总超时" in r.error.message)
        
        # 至少有一些命令因总超时而失败
        assert timeout_count > 0 or success_count < len(commands)
    
    @pytest.mark.asyncio
    async def test_execute_batch_per_command_timeout(self, engine_manager):
        """测试批量执行单命令超时"""
        call_count = 0
        
        async def timeout_execute(command, timeout, auto_reconnect=True):
            nonlocal call_count
            call_count += 1
            # 第一个命令正常执行
            if call_count == 1:
                return TclResponse(success=True, result="OK", execution_time=0.1)
            # 第二个命令超时
            else:
                await asyncio.sleep(0.5)
                return TclResponse(
                    success=False,
                    result="",
                    error=f"命令执行超时 ({timeout}秒)",
                    execution_time=timeout,
                )
        
        mock_client = Mock(spec=VivadoTcpClient)
        mock_client.is_connected = True
        mock_client.execute_tcl = timeout_execute
        
        engine_manager._tcp_client = mock_client
        engine_manager._mode = "tcp"
        engine_manager._initialized = True
        
        # 执行批量命令
        commands = ["cmd1", "cmd2", "cmd3"]
        results = await engine_manager.execute_batch(
            commands,
            timeout=10.0,  # 总超时足够长
            per_command_timeout=0.1,  # 单命令超时很短
            stop_on_error=True,
        )
        
        # 验证因错误停止
        assert len(results) == 2  # 第一个成功，第二个失败后停止
        assert results[0].success
        assert not results[1].success
    
    @pytest.mark.asyncio
    async def test_execute_batch_stop_on_error(self, engine_manager):
        """测试批量执行遇错停止"""
        mock_client = Mock(spec=VivadoTcpClient)
        mock_client.is_connected = True
        
        call_count = 0
        
        async def execute_with_error(command, timeout, auto_reconnect=True):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return TclResponse(
                    success=False,
                    result="",
                    error="Command failed",
                    execution_time=0.1,
                )
            return TclResponse(success=True, result="OK", execution_time=0.1)
        
        mock_client.execute_tcl = execute_with_error
        
        engine_manager._tcp_client = mock_client
        engine_manager._mode = "tcp"
        engine_manager._initialized = True
        
        # 执行批量命令，遇错停止
        commands = ["cmd1", "cmd2", "cmd3"]
        results = await engine_manager.execute_batch(
            commands,
            stop_on_error=True,
        )
        
        # 验证在第二个命令失败后停止
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success
    
    @pytest.mark.asyncio
    async def test_execute_batch_continue_on_error(self, engine_manager):
        """测试批量执行遇错继续"""
        mock_client = Mock(spec=VivadoTcpClient)
        mock_client.is_connected = True
        
        call_count = 0
        
        async def execute_with_error(command, timeout, auto_reconnect=True):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return TclResponse(
                    success=False,
                    result="",
                    error="Command failed",
                    execution_time=0.1,
                )
            return TclResponse(success=True, result="OK", execution_time=0.1)
        
        mock_client.execute_tcl = execute_with_error
        
        engine_manager._tcp_client = mock_client
        engine_manager._mode = "tcp"
        engine_manager._initialized = True
        
        # 执行批量命令，遇错继续
        commands = ["cmd1", "cmd2", "cmd3"]
        results = await engine_manager.execute_batch(
            commands,
            stop_on_error=False,
        )
        
        # 验证所有命令都被执行
        assert len(results) == 3
        assert results[0].success
        assert not results[1].success
        assert results[2].success


class TestTcpClientTimeout:
    """测试 VivadoTcpClient 的超时行为"""
    
    @pytest.fixture
    def tcp_client(self):
        """创建 TCP 客户端实例"""
        config = TcpConfig(timeout=30.0)
        client = VivadoTcpClient(config)
        return client
    
    @pytest.mark.asyncio
    async def test_execute_tcl_batch_uses_default_timeout(self, tcp_client):
        """测试批量执行使用默认超时配置"""
        # Mock 连接和执行
        tcp_client._state = tcp_client._state.__class__.CONNECTED
        tcp_client._lock = asyncio.Lock()
        
        async def mock_execute(command, timeout, auto_reconnect):
            return TclResponse(success=True, result="OK", execution_time=0.1)
        
        tcp_client.execute_tcl = mock_execute
        
        # 执行批量命令，不指定超时
        commands = ["cmd1", "cmd2"]
        results = await tcp_client.execute_tcl_batch(commands)
        
        # 验证结果
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_execute_tcl_batch_total_timeout(self, tcp_client):
        """测试批量执行总超时"""
        tcp_client._state = tcp_client._state.__class__.CONNECTED
        tcp_client._lock = asyncio.Lock()
        
        call_count = 0
        
        async def mock_execute(command, timeout, auto_reconnect):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.3)  # 模拟慢速执行
            return TclResponse(success=True, result="OK", execution_time=0.3)
        
        tcp_client.execute_tcl = mock_execute
        
        # 设置很短的总超时
        commands = ["cmd1", "cmd2", "cmd3", "cmd4"]
        results = await tcp_client.execute_tcl_batch(
            commands,
            timeout=0.5,  # 总超时 0.5 秒
            per_command_timeout=1.0,
        )
        
        # 验证部分命令因总超时而未执行
        assert len(results) == 4
        timeout_count = sum(
            1 for r in results 
            if not r.success and "总超时" in (r.error or "")
        )
        assert timeout_count > 0


class TestTimeoutLogging:
    """测试超时相关的日志记录"""
    
    @pytest.mark.asyncio
    async def test_command_completion_logging(self):
        """测试命令完成日志"""
        with patch('gateflow.engine.logger') as mock_logger:
            mock_client = Mock(spec=VivadoTcpClient)
            mock_client.is_connected = True
            mock_client.execute_tcl = AsyncMock(return_value=TclResponse(
                success=True,
                result="OK",
                execution_time=0.5,
            ))
            
            manager = EngineManager()
            manager._tcp_client = mock_client
            manager._mode = "tcp"
            manager._initialized = True
            
            # 执行批量命令
            commands = ["test_command"]
            await manager.execute_batch(commands)
            
            # 验证日志记录
            # 应该有命令完成的日志
            assert mock_logger.info.called
    
    @pytest.mark.asyncio
    async def test_timeout_warning_logging(self):
        """测试超时警告日志"""
        with patch('gateflow.engine.logger') as mock_logger:
            mock_client = Mock(spec=VivadoTcpClient)
            mock_client.is_connected = True
            mock_client.execute_tcl = AsyncMock(return_value=TclResponse(
                success=False,
                result="",
                error="命令执行超时 (1秒)",
                execution_time=1.0,
            ))
            
            manager = EngineManager()
            manager._tcp_client = mock_client
            manager._mode = "tcp"
            manager._initialized = True
            
            # 执行命令
            await manager.execute("test_command", timeout=1.0)
            
            # 验证超时警告日志
            assert mock_logger.warning.called
            warning_call = str(mock_logger.warning.call_args)
            assert "超时" in warning_call


class TestTimeoutSemanticsConsistency:
    """测试超时语义的一致性"""
    
    def test_timeout_config_documentation(self):
        """测试超时配置文档完整性"""
        config = TimeoutConfig()
        
        # 验证每个字段都有文档
        assert TimeoutConfig.__doc__ is not None
        assert "single_command" in TimeoutConfig.__doc__
        assert "batch_total" in TimeoutConfig.__doc__
        assert "connect" in TimeoutConfig.__doc__
        assert "idle" in TimeoutConfig.__doc__
    
    @pytest.mark.asyncio
    async def test_batch_timeout_vs_single_timeout(self):
        """测试批量超时和单命令超时的关系"""
        # 创建配置
        config = TimeoutConfig(
            single_command=10.0,
            batch_total=100.0,
        )
        
        # 验证批量超时应该大于单命令超时
        assert config.batch_total > config.single_command
        
        # 在实际使用中，单命令超时不应超过批量总超时
        # 这个关系在 EngineManager.execute_batch 中通过 min() 保证
    
    def test_timeout_parameter_naming_consistency(self):
        """测试超时参数命名的一致性"""
        # 所有批量执行方法应该使用相同的参数名
        # timeout: 总超时
        # per_command_timeout: 单命令超时
        
        # EngineManager.execute_batch
        import inspect
        sig = inspect.signature(EngineManager.execute_batch)
        params = list(sig.parameters.keys())
        assert "timeout" in params
        assert "per_command_timeout" in params
        
        # VivadoTcpClient.execute_tcl_batch
        sig = inspect.signature(VivadoTcpClient.execute_tcl_batch)
        params = list(sig.parameters.keys())
        assert "timeout" in params
        assert "per_command_timeout" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
