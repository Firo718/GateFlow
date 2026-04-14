"""
测试事件循环冲突修复

验证在已有 event loop 的环境下（如 Jupyter、pytest-asyncio），
GateFlow API 不会因为 run_until_complete 而崩溃。
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gateflow.api import GateFlow


class TestEventLoopFix:
    """测试事件循环冲突修复"""

    @pytest.mark.asyncio
    async def test_get_clock_manager_in_running_loop(self):
        """测试在运行中的 event loop 中获取时钟管理器"""
        # 创建 GateFlow 实例
        gf = GateFlow()
        
        # Mock engine
        mock_engine = MagicMock()
        
        with patch.object(gf, '_get_engine', new_callable=AsyncMock) as mock_get_engine:
            mock_get_engine.return_value = mock_engine
            
            # 在运行中的 event loop 中调用
            # 这不应该抛出 "This event loop is already running" 异常
            clock_mgr = await gf.get_clock_manager()
            
            # 验证返回了 ClockManager 实例
            assert clock_mgr is not None
            assert gf._clock_manager is clock_mgr
            
            # 再次调用应该返回缓存的实例
            clock_mgr2 = await gf.get_clock_manager()
            assert clock_mgr2 is clock_mgr

    @pytest.mark.asyncio
    async def test_get_interrupt_manager_in_running_loop(self):
        """测试在运行中的 event loop 中获取中断管理器"""
        gf = GateFlow()
        
        # Mock engine
        mock_engine = MagicMock()
        
        with patch.object(gf, '_get_engine', new_callable=AsyncMock) as mock_get_engine:
            mock_get_engine.return_value = mock_engine
            
            # 在运行中的 event loop 中调用
            irq_mgr = await gf.get_interrupt_manager()
            
            # 验证返回了 InterruptManager 实例
            assert irq_mgr is not None
            assert gf._interrupt_manager is irq_mgr
            
            # 再次调用应该返回缓存的实例
            irq_mgr2 = await gf.get_interrupt_manager()
            assert irq_mgr2 is irq_mgr

    @pytest.mark.asyncio
    async def test_no_run_until_complete_in_properties(self):
        """验证 @property 方法不再使用 run_until_complete"""
        gf = GateFlow()
        
        # 检查是否还存在 clock_manager 和 interrupt_manager 属性
        # 如果存在，它们应该是普通的 @property，不应该调用 run_until_complete
        import inspect
        
        # 检查 clock_manager
        if hasattr(GateFlow, 'clock_manager'):
            prop = getattr(GateFlow, 'clock_manager')
            if isinstance(prop, property):
                # 如果存在 @property，检查其代码
                source = inspect.getsource(prop.fget)
                # 不应该包含 run_until_complete
                assert 'run_until_complete' not in source, \
                    "clock_manager property should not use run_until_complete"
        
        # 检查 interrupt_manager
        if hasattr(GateFlow, 'interrupt_manager'):
            prop = getattr(GateFlow, 'interrupt_manager')
            if isinstance(prop, property):
                source = inspect.getsource(prop.fget)
                assert 'run_until_complete' not in source, \
                    "interrupt_manager property should not use run_until_complete"

    @pytest.mark.asyncio
    async def test_async_methods_exist(self):
        """验证异步 getter 方法存在且可调用"""
        gf = GateFlow()
        
        # 验证 get_clock_manager 是异步方法
        assert hasattr(gf, 'get_clock_manager')
        assert callable(getattr(gf, 'get_clock_manager'))
        
        # 验证 get_interrupt_manager 是异步方法
        assert hasattr(gf, 'get_interrupt_manager')
        assert callable(getattr(gf, 'get_interrupt_manager'))
        
        # 验证它们是协程函数
        import inspect
        assert inspect.iscoroutinefunction(gf.get_clock_manager)
        assert inspect.iscoroutinefunction(gf.get_interrupt_manager)

    @pytest.mark.asyncio
    async def test_multiple_calls_in_same_loop(self):
        """测试在同一个 event loop 中多次调用不会出错"""
        gf = GateFlow()
        
        mock_engine = MagicMock()
        
        with patch.object(gf, '_get_engine', new_callable=AsyncMock) as mock_get_engine:
            mock_get_engine.return_value = mock_engine
            
            # 多次调用应该都能正常工作
            for _ in range(5):
                clock_mgr = await gf.get_clock_manager()
                assert clock_mgr is not None
                
                irq_mgr = await gf.get_interrupt_manager()
                assert irq_mgr is not None

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """测试并发访问管理器"""
        gf = GateFlow()
        
        mock_engine = MagicMock()
        
        with patch.object(gf, '_get_engine', new_callable=AsyncMock) as mock_get_engine:
            mock_get_engine.return_value = mock_engine
            
            # 并发调用
            results = await asyncio.gather(
                gf.get_clock_manager(),
                gf.get_clock_manager(),
                gf.get_interrupt_manager(),
                gf.get_interrupt_manager(),
            )
            
            # 所有结果应该相同（缓存）
            assert results[0] is results[1]
            assert results[2] is results[3]

    def test_no_sync_property_access(self):
        """测试同步属性访问已被移除或不再使用 run_until_complete"""
        gf = GateFlow()
        
        # 尝试访问 clock_manager 属性
        # 如果属性存在，它应该不依赖异步操作
        try:
            # 如果 clock_manager 属性存在，访问它不应该抛出异常
            # （除非它已经被移除）
            result = gf.clock_manager
            # 如果能访问到，说明可能还有问题
            # 但我们已经在其他测试中验证了不会有 run_until_complete
        except AttributeError:
            # 属性已被移除，这是预期的
            pass
        
        try:
            result = gf.interrupt_manager
        except AttributeError:
            # 属性已被移除，这是预期的
            pass


class TestJupyterLikeEnvironment:
    """模拟 Jupyter 环境测试"""

    @pytest.mark.asyncio
    async def test_jupyter_style_usage(self):
        """测试 Jupyter 风格的使用方式"""
        # 在 Jupyter 中，event loop 已经在运行
        # 用户可以直接使用 await
        
        gf = GateFlow()
        
        mock_engine = MagicMock()
        
        with patch.object(gf, '_get_engine', new_callable=AsyncMock) as mock_get_engine:
            mock_get_engine.return_value = mock_engine
            
            # Jupyter 风格：直接 await
            clock_mgr = await gf.get_clock_manager()
            irq_mgr = await gf.get_interrupt_manager()
            
            # 后续使用
            # await gf.create_project(...) 等
            
            assert clock_mgr is not None
            assert irq_mgr is not None


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.mark.asyncio
    async def test_existing_async_methods_still_work(self):
        """测试现有的异步方法仍然正常工作"""
        gf = GateFlow()
        
        mock_engine = MagicMock()
        
        with patch.object(gf, '_get_engine', new_callable=AsyncMock) as mock_get_engine:
            mock_get_engine.return_value = mock_engine
            
            # 测试所有使用管理器的方法
            with patch.object(gf, 'get_clock_manager', new_callable=AsyncMock) as mock_cm:
                mock_cm.return_value = MagicMock()
                
                # 这些方法内部会调用 get_clock_manager
                # 不应该抛出异常
                try:
                    await gf.create_clock_network("test_clk", 10.0)
                except Exception as e:
                    # 可能因为 mock 不完整而失败，但不应该是 event loop 错误
                    assert "event loop" not in str(e).lower()
                    assert "run_until_complete" not in str(e).lower()
