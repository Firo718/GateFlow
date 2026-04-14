"""
平台注册表

提供平台模板的注册、发现和管理功能。
"""

import logging
from typing import Type

from gateflow.templates.common.base import PlatformInfo, PlatformTemplate

logger = logging.getLogger(__name__)


class PlatformRegistry:
    """
    平台注册表
    
    管理所有可用的平台模板，支持注册、查询和获取平台。
    
    Example:
        ```python
        # 注册平台
        PlatformRegistry.register(ZedboardTemplate)
        
        # 获取平台
        platform = PlatformRegistry.get("zed")
        
        # 列出所有平台
        platforms = PlatformRegistry.list_all()
        ```
    """
    
    _platforms: dict[str, Type[PlatformTemplate]] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, platform_class: Type[PlatformTemplate]) -> None:
        """
        注册平台模板
        
        Args:
            platform_class: 平台模板类
        """
        info = platform_class.get_info()
        cls._platforms[info.name.lower()] = platform_class
        logger.debug(f"注册平台: {info.name} -> {platform_class.__name__}")
    
    @classmethod
    def get(cls, name: str) -> Type[PlatformTemplate] | None:
        """
        获取平台模板类
        
        Args:
            name: 平台名称（不区分大小写）
            
        Returns:
            平台模板类，如果不存在返回 None
        """
        cls._ensure_initialized()
        return cls._platforms.get(name.lower())
    
    @classmethod
    def get_info(cls, name: str) -> PlatformInfo | None:
        """
        获取平台信息
        
        Args:
            name: 平台名称
            
        Returns:
            PlatformInfo 实例，如果不存在返回 None
        """
        platform_class = cls.get(name)
        if platform_class:
            return platform_class.get_info()
        return None
    
    @classmethod
    def list_all(cls) -> list[str]:
        """
        列出所有已注册的平台名称
        
        Returns:
            平台名称列表
        """
        cls._ensure_initialized()
        return list(cls._platforms.keys())
    
    @classmethod
    def list_by_ps_type(cls, ps_type: str) -> list[str]:
        """
        列出指定 PS 类型的平台
        
        Args:
            ps_type: PS 类型（zynq, zynqmp, versal）
            
        Returns:
            平台名称列表
        """
        cls._ensure_initialized()
        from gateflow.templates.common.base import PSType
        
        result = []
        for name, platform_class in cls._platforms.items():
            info = platform_class.get_info()
            if info.ps_type.value == ps_type.lower():
                result.append(name)
        
        return result
    
    @classmethod
    def list_by_family(cls, family: str) -> list[str]:
        """
        列出指定系列的平台
        
        Args:
            family: 器件系列
            
        Returns:
            平台名称列表
        """
        cls._ensure_initialized()
        result = []
        
        for name, platform_class in cls._platforms.items():
            info = platform_class.get_info()
            if family.lower() in info.family.lower():
                result.append(name)
        
        return result
    
    @classmethod
    def get_all_info(cls) -> dict[str, PlatformInfo]:
        """
        获取所有平台的信息
        
        Returns:
            平台名称到 PlatformInfo 的映射
        """
        cls._ensure_initialized()
        return {
            name: platform_class.get_info()
            for name, platform_class in cls._platforms.items()
        }
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """确保平台已初始化（延迟加载）"""
        if cls._initialized:
            return
        
        # 自动发现并注册平台
        cls._auto_discover()
        cls._initialized = True
    
    @classmethod
    def _auto_discover(cls) -> None:
        """自动发现并注册平台模板"""
        try:
            # 导入 Zynq 平台
            from gateflow.templates.zynq.zed import ZedboardTemplate
            from gateflow.templates.zynq.zc706 import ZC706Template
            
            cls.register(ZedboardTemplate)
            cls.register(ZC706Template)
            
        except ImportError as e:
            logger.warning(f"导入 Zynq 平台失败: {e}")
        
        try:
            # 导入 ZynqMP 平台
            from gateflow.templates.zynqmp.zcu102 import ZCU102Template
            
            cls.register(ZCU102Template)
            
        except ImportError as e:
            logger.warning(f"导入 ZynqMP 平台失败: {e}")
    
    @classmethod
    def clear(cls) -> None:
        """清空注册表（主要用于测试）"""
        cls._platforms.clear()
        cls._initialized = False


# 便捷函数
def get_platform(name: str) -> Type[PlatformTemplate] | None:
    """
    获取平台模板类
    
    Args:
        name: 平台名称
        
    Returns:
        平台模板类
    """
    return PlatformRegistry.get(name)


def list_platforms() -> list[str]:
    """
    列出所有已注册的平台
    
    Returns:
        平台名称列表
    """
    return PlatformRegistry.list_all()


def register_platform(platform_class: Type[PlatformTemplate]) -> None:
    """
    注册平台模板
    
    Args:
        platform_class: 平台模板类
    """
    PlatformRegistry.register(platform_class)
