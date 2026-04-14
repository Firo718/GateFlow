"""
IP 模块基类

提供 IP 模块的抽象基类和通用功能，参考 ADI hdl-main 项目的模块封装设计模式。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IPCategory(Enum):
    """IP 模块分类"""
    CLOCK = "clock"           # 时钟管理
    MEMORY = "memory"         # 存储器
    INTERFACE = "interface"   # 接口
    PROCESSING = "processing" # 处理系统
    DEBUG = "debug"           # 调试
    COMMUNICATION = "communication"  # 通信
    DSP = "dsp"               # 数字信号处理
    CUSTOM = "custom"         # 自定义


@dataclass
class IPProperty:
    """IP 属性定义"""
    name: str                          # 属性名称
    value: Any                         # 属性值
    description: str = ""              # 属性描述
    value_type: str = "string"         # 值类型: string, int, float, bool, list
    default: Any = None                # 默认值
    min_value: Any = None              # 最小值（数值类型）
    max_value: Any = None              # 最大值（数值类型）
    valid_values: list[Any] = field(default_factory=list)  # 有效值列表


@dataclass
class IPPort:
    """IP 端口定义"""
    name: str                    # 端口名称
    direction: str               # 方向: input, output, inout
    width: int = 1               # 位宽
    description: str = ""        # 端口描述
    is_interface: bool = False   # 是否为接口端口
    interface_type: str = ""     # 接口类型 (如 AXI4LITE, AXI4STREAM 等)
    is_clock: bool = False       # 是否为时钟端口
    is_reset: bool = False       # 是否为复位端口


@dataclass
class IPInstanceInfo:
    """IP 实例信息"""
    instance_name: str                    # 实例名称
    module_name: str                      # 模块名称
    ip_vlnv: str                          # VLNV 标识符
    properties: dict[str, Any] = field(default_factory=dict)  # 属性字典
    ports: list[IPPort] = field(default_factory=list)         # 端口列表
    connections: dict[str, str] = field(default_factory=dict) # 连接映射
    is_configured: bool = False           # 是否已配置
    is_connected: bool = False            # 是否已连接


class IPModule(ABC):
    """
    IP 模块抽象基类
    
    所有 IP 模块封装都应继承此类，实现 create、configure、connect 等方法。
    参考 ADI hdl-main 项目的设计模式，提供统一的 IP 模块接口。
    
    Example:
        class AXIGPIO(IPModule):
            ip_name = "axi_gpio"
            ip_display_name = "AXI GPIO"
            ip_category = IPCategory.INTERFACE
            
            async def create(self, instance_name: str, config: dict | None = None) -> dict:
                # 实现创建逻辑
                ...
    """
    
    # 子类必须定义的类属性
    ip_name: str = ""                    # IP 简称 (如 axi_gpio, clk_wiz)
    ip_display_name: str = ""            # IP 显示名称
    ip_category: IPCategory = IPCategory.CUSTOM  # IP 分类
    ip_vlnv_base: str = "xilinx.com:ip"  # VLNV 基础路径
    
    # 可选类属性
    ip_description: str = ""             # IP 描述
    ip_version: str = ""                 # 默认版本
    ip_documentation_url: str = ""       # 文档链接
    
    def __init__(self, tcl_engine=None):
        """
        初始化 IP 模块
        
        Args:
            tcl_engine: Tcl 执行引擎实例
        """
        self._tcl_engine = tcl_engine
        self._instances: dict[str, IPInstanceInfo] = {}
        
        # 验证必要属性
        if not self.ip_name:
            raise ValueError(f"{self.__class__.__name__} 必须定义 ip_name 类属性")
    
    @property
    def ip_vlnv(self) -> str:
        """
        获取 IP 的完整 VLNV 标识符
        
        Returns:
            VLNV 字符串 (Vendor:Library:Name:Version)
        """
        vlnv = f"{self.ip_vlnv_base}:{self.ip_name}"
        if self.ip_version:
            vlnv += f":{self.ip_version}"
        return vlnv
    
    @property
    def default_version(self) -> str:
        """获取默认版本"""
        return self.ip_version
    
    @abstractmethod
    async def create(
        self,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建 IP 实例
        
        Args:
            instance_name: 实例名称
            config: 配置字典
        
        Returns:
            创建结果字典，包含:
            - success: 是否成功
            - instance_name: 实例名称
            - module_name: 模块名称
            - message: 结果消息
            - error: 错误信息（如果失败）
        
        Example:
            result = await gpio.create("axi_gpio_0", {"gpio_width": 8})
        """
        pass
    
    async def configure(
        self,
        instance_name: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        配置 IP 参数
        
        Args:
            instance_name: 实例名称
            config: 配置字典
        
        Returns:
            配置结果字典
        """
        if not self._tcl_engine:
            return {
                "success": False,
                "error": "Tcl 引擎未初始化",
            }
        
        if instance_name not in self._instances:
            return {
                "success": False,
                "error": f"实例 {instance_name} 不存在",
            }
        
        # 生成配置命令
        commands = self._generate_config_commands(instance_name, config)
        
        # 执行配置
        result = await self._tcl_engine.execute_async(commands)
        
        if result.success:
            # 更新实例信息
            self._instances[instance_name].properties.update(config)
            self._instances[instance_name].is_configured = True
            logger.info(f"IP {instance_name} 配置成功")
        else:
            logger.error(f"IP {instance_name} 配置失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    async def connect(
        self,
        instance_name: str,
        connections: dict[str, str],
    ) -> dict[str, Any]:
        """
        连接 IP 引脚
        
        Args:
            instance_name: 实例名称
            connections: 连接映射字典，格式为 {本端口: 目标端口}
        
        Returns:
            连接结果字典
        """
        if not self._tcl_engine:
            return {
                "success": False,
                "error": "Tcl 引擎未初始化",
            }
        
        if instance_name not in self._instances:
            return {
                "success": False,
                "error": f"实例 {instance_name} 不存在",
            }
        
        commands = []
        
        for source_port, target_port in connections.items():
            # 判断是接口连接还是普通连接
            is_interface = self._is_interface_port(instance_name, source_port)
            
            if is_interface:
                cmd = f'connect_bd_intf_net [get_bd_intf_pins {instance_name}/{source_port}] [get_bd_intf_pins {target_port}]'
            else:
                cmd = f'connect_bd_net [get_bd_pins {instance_name}/{source_port}] [get_bd_pins {target_port}]'
            
            commands.append(cmd)
        
        result = await self._tcl_engine.execute_async(commands)
        
        if result.success:
            self._instances[instance_name].connections.update(connections)
            logger.info(f"IP {instance_name} 连接成功")
        else:
            logger.error(f"IP {instance_name} 连接失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    async def remove(self, instance_name: str) -> dict[str, Any]:
        """
        移除 IP 实例
        
        Args:
            instance_name: 实例名称
        
        Returns:
            移除结果字典
        """
        if not self._tcl_engine:
            return {
                "success": False,
                "error": "Tcl 引擎未初始化",
            }
        
        if instance_name not in self._instances:
            return {
                "success": False,
                "error": f"实例 {instance_name} 不存在",
            }
        
        cmd = f'delete_bd_objs [get_bd_cells {instance_name}]'
        result = await self._tcl_engine.execute_async(cmd)
        
        if result.success:
            del self._instances[instance_name]
            logger.info(f"IP {instance_name} 移除成功")
        else:
            logger.error(f"IP {instance_name} 移除失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "errors": result.errors,
        }
    
    def get_instance_info(self, instance_name: str) -> IPInstanceInfo | None:
        """
        获取实例信息
        
        Args:
            instance_name: 实例名称
        
        Returns:
            实例信息对象，不存在则返回 None
        """
        return self._instances.get(instance_name)
    
    def list_instances(self) -> list[str]:
        """
        列出所有实例名称
        
        Returns:
            实例名称列表
        """
        return list(self._instances.keys())
    
    def get_default_config(self) -> dict[str, Any]:
        """
        获取默认配置
        
        子类可以重写此方法提供默认配置。
        
        Returns:
            默认配置字典
        """
        return {}
    
    def get_available_properties(self) -> list[IPProperty]:
        """
        获取可配置属性列表
        
        子类可以重写此方法提供属性定义。
        
        Returns:
            属性定义列表
        """
        return []
    
    def get_ports(self) -> list[IPPort]:
        """
        获取端口列表
        
        子类可以重写此方法提供端口定义。
        
        Returns:
            端口定义列表
        """
        return []
    
    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        验证配置参数
        
        Args:
            config: 配置字典
        
        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        available_props = self.get_available_properties()
        
        for prop in available_props:
            if prop.name in config:
                value = config[prop.name]
                
                # 类型检查
                if prop.value_type == "int":
                    if not isinstance(value, int):
                        errors.append(f"属性 {prop.name} 应为整数类型")
                    elif prop.min_value is not None and value < prop.min_value:
                        errors.append(f"属性 {prop.name} 值 {value} 小于最小值 {prop.min_value}")
                    elif prop.max_value is not None and value > prop.max_value:
                        errors.append(f"属性 {prop.name} 值 {value} 大于最大值 {prop.max_value}")
                
                elif prop.value_type == "float":
                    if not isinstance(value, (int, float)):
                        errors.append(f"属性 {prop.name} 应为浮点类型")
                
                elif prop.value_type == "bool":
                    if not isinstance(value, bool):
                        errors.append(f"属性 {prop.name} 应为布尔类型")
                
                # 有效值检查
                if prop.valid_values and value not in prop.valid_values:
                    errors.append(f"属性 {prop.name} 值 {value} 不在有效值列表中")
        
        return len(errors) == 0, errors
    
    # ==================== 内部方法 ====================
    
    def _generate_create_command(self, instance_name: str) -> str:
        """
        生成创建 IP 的 Tcl 命令
        
        Args:
            instance_name: 实例名称
        
        Returns:
            Tcl 命令字符串
        """
        return f'create_bd_cell -type ip -vlnv {self.ip_vlnv} {instance_name}'
    
    def _generate_config_commands(
        self,
        instance_name: str,
        config: dict[str, Any],
    ) -> str:
        """
        生成配置 IP 的 Tcl 命令
        
        Args:
            instance_name: 实例名称
            config: 配置字典
        
        Returns:
            Tcl 命令字符串
        """
        prop_list = []
        for key, value in config.items():
            if isinstance(value, bool):
                prop_list.append(f"CONFIG.{key} {'true' if value else 'false'}")
            elif isinstance(value, str):
                prop_list.append(f'CONFIG.{key} "{value}"')
            else:
                prop_list.append(f"CONFIG.{key} {value}")
        
        props_str = ' '.join(prop_list)
        return f'set_property -dict [list {props_str}] [get_bd_cells {instance_name}]'
    
    def _register_instance(
        self,
        instance_name: str,
        module_name: str,
        config: dict[str, Any] | None = None,
    ) -> IPInstanceInfo:
        """
        注册实例信息
        
        Args:
            instance_name: 实例名称
            module_name: 模块名称
            config: 初始配置
        
        Returns:
            实例信息对象
        """
        info = IPInstanceInfo(
            instance_name=instance_name,
            module_name=module_name,
            ip_vlnv=self.ip_vlnv,
            properties=config or {},
            ports=self.get_ports(),
        )
        self._instances[instance_name] = info
        return info
    
    def _is_interface_port(self, instance_name: str, port_name: str) -> bool:
        """
        判断是否为接口端口
        
        Args:
            instance_name: 实例名称
            port_name: 端口名称
        
        Returns:
            是否为接口端口
        """
        for port in self.get_ports():
            if port.name == port_name:
                return port.is_interface
        return False
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(ip_name={self.ip_name}, vlnv={self.ip_vlnv})"


class IPModuleRegistry:
    """
    IP 模块注册表
    
    用于注册和获取 IP 模块类。
    """
    
    _modules: dict[str, type[IPModule]] = {}
    
    @classmethod
    def register(cls, module_class: type[IPModule]) -> type[IPModule]:
        """
        注册 IP 模块类
        
        Args:
            module_class: IP 模块类
        
        Returns:
            注册的模块类（支持装饰器用法）
        """
        if not issubclass(module_class, IPModule):
            raise TypeError(f"{module_class} 必须是 IPModule 的子类")
        
        name = module_class.ip_name
        if name in cls._modules:
            logger.warning(f"IP 模块 {name} 已存在，将被覆盖")
        
        cls._modules[name] = module_class
        logger.debug(f"注册 IP 模块: {name}")
        return module_class
    
    @classmethod
    def get(cls, name: str) -> type[IPModule] | None:
        """
        获取 IP 模块类
        
        Args:
            name: IP 名称
        
        Returns:
            IP 模块类，不存在则返回 None
        """
        return cls._modules.get(name)
    
    @classmethod
    def list_modules(cls) -> list[str]:
        """
        列出所有已注册的 IP 模块名称
        
        Returns:
            IP 名称列表
        """
        return list(cls._modules.keys())
    
    @classmethod
    def create_instance(cls, name: str, tcl_engine=None) -> IPModule | None:
        """
        创建 IP 模块实例
        
        Args:
            name: IP 名称
            tcl_engine: Tcl 引擎
        
        Returns:
            IP 模块实例，不存在则返回 None
        """
        module_class = cls.get(name)
        if module_class:
            return module_class(tcl_engine)
        return None


def register_module(module_class: type[IPModule]) -> type[IPModule]:
    """
    注册 IP 模块的装饰器
    
    Args:
        module_class: IP 模块类
    
    Returns:
        注册的模块类
    
    Example:
        @register_module
        class AXIGPIO(IPModule):
            ip_name = "axi_gpio"
            ...
    """
    return IPModuleRegistry.register(module_class)
