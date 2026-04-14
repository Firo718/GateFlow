"""
GateFlow Vivado Tcl 执行引擎

该模块提供与 AMD Vivado 工具的 Tcl 接口交互能力，
支持项目创建、综合、实现、比特流生成等完整流程。

使用示例:
    from gateflow.vivado import TclEngine, ProjectManager, SynthesisManager
    
    # 创建 Tcl 执行引擎
    engine = TclEngine()
    
    # 创建项目管理器
    project_mgr = ProjectManager(engine)
    project_mgr.create_project("my_project", Path("./my_project"), "xc7z020clg400-1")
    
    # 运行综合
    synth_mgr = SynthesisManager(engine)
    synth_mgr.run_synthesis()
"""

# 核心引擎
from .tcl_engine import (
    TclEngine,
    TclResult,
    VivadoDetector,
    VivadoInfo,
    VivadoVersion,
)

# 项目管理
from .project import (
    FileType,
    ProjectConfig,
    ProjectManager,
    ProjectTclGenerator,
)

# 综合
from .synthesis import (
    ResourceUtilization,
    RunStatus,
    SynthesisManager,
    SynthesisResult,
    SynthesisStrategy,
    SynthesisTclGenerator,
)

# 实现
from .implementation import (
    BitstreamFormat,
    ImplementationManager,
    ImplementationResult,
    ImplementationStrategy,
    ImplementationTclGenerator,
    TimingSummary,
)

# 时序约束
from .constraints import (
    ClockConstraint,
    ClockSense,
    ConstraintInfo,
    ConstraintType,
    ConstraintsManager,
    ConstraintsTclGenerator,
    DelayType,
    FalsePathConstraint,
    GeneratedClockConstraint,
    InputDelayConstraint,
    MaxDelayConstraint,
    MinDelayConstraint,
    MulticycleConstraint,
    OutputDelayConstraint,
)

# 硬件编程
from .hardware import (
    DeviceType,
    HardwareDevice,
    HardwareManager,
    HardwareServer,
    HardwareTclGenerator,
    JtagState,
    MemoryDevice,
    ProgrammingResult,
    ProgrammingStatus,
)

# 仿真支持
from .simulation import (
    SimulatorType,
    SimulationMode,
    SimulationStatus,
    SimulationConfig,
    TestbenchConfig,
    SimulationResult,
    WaveSignal,
    SimulationTclGenerator,
    SimulationManager,
    TestbenchRunner,
)

# Block Design
from .block_design import (
    BDConnection,
    BDInterfaceType,
    BDIPInstance,
    BDPort,
    BDAutoConnectRule,
    BlockDesignConfig,
    BlockDesignManager,
    BlockDesignTclGenerator,
    ZynqPSConfig,
)

# IP 配置
from .ip_config import (
    IPType,
    IPInterfaceType,
    MemoryType,
    IPConfig,
    ClockingWizardConfig,
    FIFOConfig,
    BRAMConfig,
    AXIInterconnectConfig,
    DMAConfig,
    ZynqPSConfig as IPC_ZynqPSConfig,
    XADCConfig,
    ILAConfig,
    IPTclGenerator,
    IPManager,
    create_clocking_wizard_config,
    create_fifo_config,
    create_bram_config,
)

# IP 工具
from .ip_utils import (
    IPInfo,
    IPDefinition,
    IPRegistry,
    IPInstanceHelper,
    find_ip_vlnv,
    create_ip_instance,
)

# Tcl Server
from .tcl_server import (
    VivadoInstallation,
    VivadoDetector as TclServerVivadoDetector,
    TclServerInstaller,
    install_tcl_server,
    uninstall_tcl_server,
    list_vivado_installations,
    DEFAULT_PORT,
)

# TCP 客户端
from .tcp_client import (
    ConnectionState,
    TcpConfig,
    TclResponse,
    VivadoTcpClient,
    TcpClientManager,
    execute_tcl_command,
    execute_tcl_commands,
)

__all__ = [
    # 核心引擎
    "TclEngine",
    "TclResult",
    "VivadoDetector",
    "VivadoInfo",
    "VivadoVersion",
    # 项目管理
    "FileType",
    "ProjectConfig",
    "ProjectManager",
    "ProjectTclGenerator",
    # 综合
    "ResourceUtilization",
    "RunStatus",
    "SynthesisManager",
    "SynthesisResult",
    "SynthesisStrategy",
    "SynthesisTclGenerator",
    # 实现
    "BitstreamFormat",
    "ImplementationManager",
    "ImplementationResult",
    "ImplementationStrategy",
    "ImplementationTclGenerator",
    "TimingSummary",
    # 时序约束
    "ClockConstraint",
    "ClockSense",
    "ConstraintInfo",
    "ConstraintType",
    "ConstraintsManager",
    "ConstraintsTclGenerator",
    "DelayType",
    "FalsePathConstraint",
    "GeneratedClockConstraint",
    "InputDelayConstraint",
    "MaxDelayConstraint",
    "MinDelayConstraint",
    "MulticycleConstraint",
    "OutputDelayConstraint",
    # 硬件编程
    "DeviceType",
    "HardwareDevice",
    "HardwareManager",
    "HardwareServer",
    "HardwareTclGenerator",
    "JtagState",
    "MemoryDevice",
    "ProgrammingResult",
    "ProgrammingStatus",
    # 仿真支持
    "SimulatorType",
    "SimulationMode",
    "SimulationStatus",
    "SimulationConfig",
    "TestbenchConfig",
    "SimulationResult",
    "WaveSignal",
    "SimulationTclGenerator",
    "SimulationManager",
    "TestbenchRunner",
    # Block Design
    "BDConnection",
    "BDInterfaceType",
    "BDIPInstance",
    "BDPort",
    "BDAutoConnectRule",
    "BlockDesignConfig",
    "BlockDesignManager",
    "BlockDesignTclGenerator",
    "ZynqPSConfig",
    # IP 配置
    "IPType",
    "IPInterfaceType",
    "MemoryType",
    "IPConfig",
    "ClockingWizardConfig",
    "FIFOConfig",
    "BRAMConfig",
    "AXIInterconnectConfig",
    "DMAConfig",
    "ZynqPSConfig",
    "XADCConfig",
    "ILAConfig",
    "IPTclGenerator",
    "IPManager",
    "create_clocking_wizard_config",
    "create_fifo_config",
    "create_bram_config",
    # IP 工具
    "IPInfo",
    "IPDefinition",
    "IPRegistry",
    "IPInstanceHelper",
    "find_ip_vlnv",
    "create_ip_instance",
    # Tcl Server
    "VivadoInstallation",
    "TclServerVivadoDetector",
    "TclServerInstaller",
    "install_tcl_server",
    "uninstall_tcl_server",
    "list_vivado_installations",
    "DEFAULT_PORT",
    # TCP 客户端
    "ConnectionState",
    "TcpConfig",
    "TclResponse",
    "VivadoTcpClient",
    "TcpClientManager",
    "execute_tcl_command",
    "execute_tcl_commands",
]

__version__ = "0.1.0"
__author__ = "GateFlow Team"
