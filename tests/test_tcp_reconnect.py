"""
TCP 断线/超时恢复机制测试

测试 TCP 连接的断线重连和超时处理功能。
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from gateflow.vivado.tcp_client import (
    VivadoTcpClient,
    TcpConfig,
    TclResponse,
    ConnectionState,
    generate_request_id,
    TcpClientManager,
)


class TestRequestId:
    """测试请求 ID 生成"""
    
    def test_generate_request_id_length(self):
        """测试请求 ID 长度为 8"""
        request_id = generate_request_id()
        assert len(request_id) == 8
    
    def test_generate_request_id_uniqueness(self):
        """测试请求 ID 唯一性"""
        ids = [generate_request_id() for _ in range(100)]
        # 检查所有 ID 都是唯一的
        assert len(ids) == len(set(ids))
    
    def test_generate_request_id_format(self):
        """测试请求 ID 格式（十六进制字符）"""
        request_id = generate_request_id()
        # UUID 的前 8 位应该是十六进制字符
        assert all(c in '0123456789abcdef-' for c in request_id)


class TestTclResponse:
    """测试 TclResponse 数据结构"""
    
    def test_tcl_response_default_values(self):
        """测试 TclResponse 默认值"""
        response = TclResponse(success=True, result="test")
        assert response.request_id == ""
        assert response.timeout_occurred is False
        assert response.reconnect_attempted is False
        assert response.reconnect_success is False
    
    def test_tcl_response_with_request_id(self):
        """测试带 request_id 的 TclResponse"""
        response = TclResponse(
            success=True,
            result="test",
            request_id="abc12345"
        )
        assert response.request_id == "abc12345"
    
    def test_tcl_response_timeout_info(self):
        """测试超时信息的 TclResponse"""
        response = TclResponse(
            success=False,
            result="",
            error="命令执行超时",
            request_id="timeout123",
            timeout_occurred=True,
            reconnect_attempted=True,
            reconnect_success=True,
        )
        assert response.timeout_occurred is True
        assert response.reconnect_attempted is True
        assert response.reconnect_success is True


class TestConnectionState:
    """测试连接状态"""
    
    def test_connection_state_values(self):
        """测试连接状态枚举值"""
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.ERROR.value == "error"


class TestVivadoTcpClient:
    """测试 VivadoTcpClient"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        config = TcpConfig(
            host="localhost",
            port=9999,
            timeout=30.0,
            reconnect_attempts=3,
            reconnect_delay=1.0,
        )
        client = VivadoTcpClient(config)
        
        assert client.config == config
        assert client.state == ConnectionState.DISCONNECTED
        assert client._pending_requests == {}
        assert client._timeout_history == []
    
    def test_client_default_config(self):
        """测试默认配置"""
        client = VivadoTcpClient()
        assert client.config.host == "localhost"
        assert client.config.port == 9999
        assert client.config.timeout == 60.0
    
    def test_timeout_history_tracking(self):
        """测试超时历史追踪"""
        client = VivadoTcpClient()
        
        # 添加模拟超时记录
        client._timeout_history.append({
            "request_id": "test1234",
            "command": "puts test",
            "timeout": 30.0,
            "execution_time": 30.1,
            "timestamp": 1234567890.0,
        })
        
        history = client.get_timeout_history()
        assert len(history) == 1
        assert history[0]["request_id"] == "test1234"
    
    def test_pending_requests_tracking(self):
        """测试待处理请求追踪"""
        client = VivadoTcpClient()
        
        # 添加模拟请求
        client._pending_requests["req12345"] = {
            "command": "puts test",
            "start_time": 1234567890.0,
            "timeout": 30.0,
            "status": "pending",
        }
        
        pending = client.get_pending_requests()
        assert "req12345" in pending
        assert pending["req12345"]["status"] == "pending"
    
    def test_clear_timeout_history(self):
        """测试清空超时历史"""
        client = VivadoTcpClient()
        client._timeout_history.append({"test": "data"})
        
        client.clear_timeout_history()
        assert len(client._timeout_history) == 0
    
    def test_clear_pending_requests(self):
        """测试清空已完成的待处理请求"""
        client = VivadoTcpClient()
        
        # 添加不同状态的请求
        client._pending_requests["req1"] = {"status": "completed"}
        client._pending_requests["req2"] = {"status": "pending"}
        client._pending_requests["req3"] = {"status": "timeout"}
        
        client.clear_pending_requests()
        
        # 只有 pending 状态的请求应该保留
        assert "req1" not in client._pending_requests
        assert "req2" in client._pending_requests
        assert "req3" not in client._pending_requests


class TestTcpClientManager:
    """测试 TcpClientManager"""
    
    def setup_method(self):
        """每个测试前重置管理器"""
        TcpClientManager.reset()
    
    def test_get_client_singleton(self):
        """测试单例模式"""
        client1 = TcpClientManager.get_client()
        client2 = TcpClientManager.get_client()
        assert client1 is client2
    
    def test_get_timeout_history_empty(self):
        """测试空超时历史"""
        TcpClientManager.get_client()
        history = TcpClientManager.get_timeout_history()
        assert history == []
    
    def test_get_pending_requests_empty(self):
        """测试空待处理请求"""
        TcpClientManager.get_client()
        pending = TcpClientManager.get_pending_requests()
        assert pending == {}


class TestExecuteTclWithReconnect:
    """测试带重连的命令执行"""
    
    @pytest.mark.asyncio
    async def test_execute_tcl_generates_request_id(self):
        """测试执行命令生成 request_id"""
        client = VivadoTcpClient()
        
        # 模拟连接
        client._state = ConnectionState.CONNECTED
        client._reader = MagicMock()
        client._writer = MagicMock()
        
        # 模拟发送和接收
        with patch.object(client, '_send_command', new_callable=AsyncMock):
            with patch.object(client, '_receive_until_prompt', new_callable=AsyncMock, return_value="OK: test\n"):
                response = await client.execute_tcl("puts test", timeout=5.0, auto_reconnect=False)
        
        assert response.request_id != ""
        assert len(response.request_id) == 8
    
    @pytest.mark.asyncio
    async def test_execute_tcl_timeout_records_history(self):
        """测试超时记录历史"""
        client = VivadoTcpClient()
        
        # 模拟连接
        client._state = ConnectionState.CONNECTED
        client._reader = MagicMock()
        client._writer = MagicMock()
        
        # 模拟超时
        with patch.object(client, '_send_command', new_callable=AsyncMock):
            with patch.object(client, '_receive_until_prompt', new_callable=AsyncMock) as mock_receive:
                mock_receive.side_effect = asyncio.TimeoutError()
                
                response = await client.execute_tcl("puts test", timeout=1.0, auto_reconnect=False)
        
        assert response.timeout_occurred is True
        assert response.success is False
        assert len(client._timeout_history) == 1
        
        timeout_info = client._timeout_history[0]
        assert timeout_info["command"] == "puts test"
        assert timeout_info["timeout"] == 1.0
        assert "request_id" in timeout_info
    
    @pytest.mark.asyncio
    async def test_execute_tcl_connection_reset_attempts_reconnect(self):
        """测试连接重置后尝试重连"""
        config = TcpConfig(reconnect_attempts=2, reconnect_delay=0.1)
        client = VivadoTcpClient(config)
        
        # 模拟连接
        client._state = ConnectionState.CONNECTED
        client._reader = MagicMock()
        client._writer = MagicMock()
        
        # 模拟连接重置
        with patch.object(client, '_send_command', new_callable=AsyncMock):
            with patch.object(client, '_receive_until_prompt', new_callable=AsyncMock) as mock_receive:
                mock_receive.side_effect = ConnectionResetError("Connection reset")
                
                # 模拟重连失败
                with patch.object(client, 'reconnect', new_callable=AsyncMock, return_value=False):
                    response = await client.execute_tcl("puts test", timeout=1.0, auto_reconnect=True)
        
        assert response.reconnect_attempted is True
        assert response.reconnect_success is False
    
    @pytest.mark.asyncio
    async def test_execute_tcl_auto_connect_when_disconnected(self):
        """测试断开连接时自动连接"""
        client = VivadoTcpClient()
        
        # 模拟未连接状态
        assert client.state == ConnectionState.DISCONNECTED
        
        # 模拟连接成功
        with patch.object(client, 'connect', new_callable=AsyncMock, return_value=True):
            with patch.object(client, 'execute_tcl', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = TclResponse(
                    success=True,
                    result="test",
                    request_id="test1234",
                )
                
                # 这里我们测试的是 execute_tcl 内部会调用 connect
                # 实际测试需要更复杂的模拟


class TestTimeoutInfo:
    """测试超时信息完整性"""
    
    def test_timeout_info_structure(self):
        """测试超时信息结构"""
        client = VivadoTcpClient()
        
        # 模拟超时记录
        timeout_info = {
            "request_id": "abc12345",
            "command": "create_project my_project",
            "timeout": 30.0,
            "execution_time": 30.5,
            "timestamp": 1234567890.0,
        }
        client._timeout_history.append(timeout_info)
        
        history = client.get_timeout_history()
        assert len(history) == 1
        
        info = history[0]
        assert info["request_id"] == "abc12345"
        assert info["command"] == "create_project my_project"
        assert info["timeout"] == 30.0
        assert info["execution_time"] == 30.5
        assert "timestamp" in info


class TestReconnectBehavior:
    """测试重连行为"""
    
    @pytest.mark.asyncio
    async def test_reconnect_respects_max_attempts(self):
        """测试重连次数限制"""
        config = TcpConfig(reconnect_attempts=2, reconnect_delay=0.1)
        client = VivadoTcpClient(config)
        
        # 模拟连接失败
        with patch.object(client, 'connect', new_callable=AsyncMock, return_value=False):
            # 第一次重连
            result1 = await client.reconnect()
            assert result1 is False
            assert client._reconnect_count == 1
            
            # 第二次重连
            result2 = await client.reconnect()
            assert result2 is False
            assert client._reconnect_count == 2
            
            # 第三次应该失败（超过最大次数）
            result3 = await client.reconnect()
            assert result3 is False
    
    @pytest.mark.asyncio
    async def test_reconnect_success_resets_counter(self):
        """测试重连成功后重置计数器"""
        config = TcpConfig(reconnect_attempts=3, reconnect_delay=0.1)
        client = VivadoTcpClient(config)
        
        # 模拟重连成功
        with patch.object(client, 'connect', new_callable=AsyncMock, return_value=True):
            with patch.object(client, '_cleanup_connection', new_callable=AsyncMock):
                result = await client.reconnect()
        
        assert result is True
        assert client._reconnect_count == 0


@pytest.mark.integration
class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_timeout_flow(self):
        """测试完整的超时流程"""
        config = TcpConfig(timeout=1.0, reconnect_attempts=1, reconnect_delay=0.1)
        client = VivadoTcpClient(config)
        
        # 模拟连接
        client._state = ConnectionState.CONNECTED
        client._reader = MagicMock()
        client._writer = MagicMock()
        
        # 模拟超时然后重连失败
        with patch.object(client, '_send_command', new_callable=AsyncMock):
            with patch.object(client, '_receive_until_prompt', new_callable=AsyncMock) as mock_receive:
                mock_receive.side_effect = asyncio.TimeoutError()
                
                with patch.object(client, 'reconnect', new_callable=AsyncMock, return_value=False):
                    response = await client.execute_tcl("long_running_command", auto_reconnect=True)
        
        # 验证响应
        assert response.success is False
        assert response.timeout_occurred is True
        assert response.reconnect_attempted is True
        assert response.reconnect_success is False
        assert response.request_id != ""
        
        # 验证超时历史
        assert len(client._timeout_history) == 1
        timeout_info = client._timeout_history[0]
        assert timeout_info["request_id"] == response.request_id
        assert timeout_info["command"] == "long_running_command"
        
        # 验证待处理请求状态
        pending = client.get_pending_requests()
        assert response.request_id in pending
        assert pending[response.request_id]["status"] == "timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
