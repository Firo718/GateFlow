"""
Vivado 项目管理 Tcl 命令封装

该模块提供项目创建、打开、文件管理等操作的 Tcl 命令生成功能。
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileType(Enum):
    """文件类型枚举"""
    VERILOG = "verilog"
    VERILOG_HEADER = "verilog_header"
    VHDL = "vhdl"
    VHDL_2008 = "vhdl_2008"
    SYSTEM_VERILOG = "systemverilog"
    XDC = "xdc"
    TCL = "tcl"
    MEM = "mem"
    BD = "bd"  # Block Design
    IP = "ip"
    CONSTRAINT = "constraint"
    SIMULATION = "simulation"
    DATA = "data"


@dataclass
class ProjectConfig:
    """项目配置信息"""
    name: str  # 项目名称
    path: Path  # 项目路径
    part: str  # 目标器件型号
    board: Optional[str] = None  # 目标开发板（可选）
    language: str = "Verilog"  # 默认语言
    simulator: str = "ModelSim"  # 仿真器


class ProjectTclGenerator:
    """
    项目管理 Tcl 命令生成器
    
    生成用于项目创建、打开、配置等操作的 Tcl 命令。
    """
    
    @staticmethod
    def create_project_tcl(
        name: str,
        path: Path,
        part: str,
        board: Optional[str] = None,
        force: bool = True,
    ) -> str:
        """
        生成创建项目的 Tcl 命令
        
        Args:
            name: 项目名称
            path: 项目路径
            part: 目标器件型号（如 xc7z020clg400-1）
            board: 目标开发板（可选，如 zc702）
            force: 是否强制覆盖已存在的项目
            
        Returns:
            Tcl 命令字符串
        """
        # 构建基本命令
        cmd_parts = [
            f'create_project "{name}" "{path}"',
        ]
        
        # 添加器件型号
        cmd_parts.append(f'-part "{part}"')
        
        # 添加开发板（如果指定）
        if board:
            cmd_parts.append(f'-board "{board}"')
        
        # 强制覆盖
        if force:
            cmd_parts.append('-force')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def create_project_full_tcl(config: ProjectConfig) -> list[str]:
        """
        生成完整的创建项目 Tcl 命令序列
        
        Args:
            config: 项目配置
            
        Returns:
            Tcl 命令列表
        """
        commands = []
        
        # 创建项目
        commands.append(
            ProjectTclGenerator.create_project_tcl(
                name=config.name,
                path=config.path,
                part=config.part,
                board=config.board,
            )
        )
        
        # 设置目标语言
        commands.append(
            f'set_property target_language {config.language} [current_project]'
        )
        
        # 设置仿真器
        commands.append(
            f'set_property simulator_language {config.language} [current_project]'
        )
        
        # 设置默认库
        commands.append(
            'set_property default_lib work [current_project]'
        )
        
        return commands
    
    @staticmethod
    def open_project_tcl(path: Path) -> str:
        """
        生成打开项目的 Tcl 命令
        
        Args:
            path: 项目文件路径（.xpr 文件）
            
        Returns:
            Tcl 命令字符串
        """
        return f'open_project "{path}"'
    
    @staticmethod
    def close_project_tcl() -> str:
        """
        生成关闭项目的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_project'
    
    @staticmethod
    def save_project_tcl() -> str:
        """
        生成保存项目的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'save_project'
    
    @staticmethod
    def add_files_tcl(
        files: list[Path],
        file_type: Optional[FileType] = None,
        library: Optional[str] = None,
    ) -> list[str]:
        """
        生成添加文件的 Tcl 命令
        
        Args:
            files: 文件路径列表
            file_type: 文件类型（可选，自动检测）
            library: VHDL 库名（可选）
            
        Returns:
            Tcl 命令列表
        """
        commands = []
        
        # 将文件路径转换为 Tcl 格式
        file_list = ' '.join(f'"{f}"' for f in files)
        
        # 添加文件命令
        add_cmd = f'add_files {{{file_list}}}'
        
        if file_type:
            add_cmd += f' -file_type {file_type.value}'
        
        commands.append(add_cmd)
        
        # 如果指定了库，设置文件属性
        if library and file_type in [FileType.VHDL, FileType.VHDL_2008]:
            for file in files:
                commands.append(
                    f'set_property library {library} [get_files "{file}"]'
                )
        
        return commands
    
    @staticmethod
    def add_source_files_tcl(
        files: list[Path],
        file_type: Optional[FileType] = None,
    ) -> str:
        """
        生成添加源文件的 Tcl 命令
        
        Args:
            files: 文件路径列表
            file_type: 文件类型
            
        Returns:
            Tcl 命令字符串
        """
        file_list = ' '.join(f'"{f}"' for f in files)
        cmd = f'add_files -fileset sources_1 {{{file_list}}}'
        
        if file_type:
            cmd += f' -file_type {file_type.value}'
        
        return cmd
    
    @staticmethod
    def add_constraint_files_tcl(files: list[Path]) -> str:
        """
        生成添加约束文件的 Tcl 命令
        
        Args:
            files: 约束文件路径列表
            
        Returns:
            Tcl 命令字符串
        """
        file_list = ' '.join(f'"{f}"' for f in files)
        return f'add_files -fileset constrs_1 {{{file_list}}}'
    
    @staticmethod
    def add_simulation_files_tcl(
        files: list[Path],
        sim_set: str = "sim_1",
    ) -> str:
        """
        生成添加仿真文件的 Tcl 命令
        
        Args:
            files: 仿真文件路径列表
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        file_list = ' '.join(f'"{f}"' for f in files)
        return f'add_files -fileset {sim_set} {{{file_list}}}'
    
    @staticmethod
    def remove_files_tcl(files: list[Path]) -> str:
        """
        生成移除文件的 Tcl 命令
        
        Args:
            files: 要移除的文件路径列表
            
        Returns:
            Tcl 命令字符串
        """
        file_list = ' '.join(f'"{f}"' for f in files)
        return f'remove_files {{{file_list}}}'
    
    @staticmethod
    def set_top_module_tcl(module: str, fileset: str = "sources_1") -> str:
        """
        生成设置顶层模块的 Tcl 命令
        
        Args:
            module: 顶层模块名称
            fileset: 文件集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property top {module} [get_filesets {fileset}]'
    
    @staticmethod
    def set_top_module_auto_tcl(fileset: str = "sources_1") -> str:
        """
        生成自动设置顶层模块的 Tcl 命令
        
        Args:
            fileset: 文件集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property top [get_property top [current_fileset]] [get_filesets {fileset}]'
    
    @staticmethod
    def update_compile_order_tcl(fileset: str = "sources_1") -> str:
        """
        生成更新编译顺序的 Tcl 命令
        
        Args:
            fileset: 文件集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'update_compile_order -fileset {fileset}'
    
    @staticmethod
    def get_project_info_tcl() -> list[str]:
        """
        生成获取项目信息的 Tcl 命令
        
        Returns:
            Tcl 命令列表
        """
        return [
            'set project_name [get_property name [current_project]]',
            'set project_dir [get_property directory [current_project]]',
            'set part_name [get_property part [current_project]]',
            'set board_part [get_property board_part [current_project]]',
            'set target_language [get_property target_language [current_project]]',
            'puts "Project: $project_name"',
            'puts "Directory: $project_dir"',
            'puts "Part: $part_name"',
            'puts "Board: $board_part"',
            'puts "Language: $target_language"',
        ]
    
    @staticmethod
    def get_filesets_tcl() -> str:
        """
        生成获取文件集列表的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_filesets'
    
    @staticmethod
    def get_files_tcl(fileset: str = "sources_1") -> str:
        """
        生成获取文件列表的 Tcl 命令
        
        Args:
            fileset: 文件集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_files -of_objects [get_filesets {fileset}]'
    
    @staticmethod
    def set_property_tcl(
        property_name: str,
        value: str,
        object_type: str = "current_project",
        object_name: Optional[str] = None,
    ) -> str:
        """
        生成设置属性的 Tcl 命令
        
        Args:
            property_name: 属性名称
            value: 属性值
            object_type: 对象类型
            object_name: 对象名称
            
        Returns:
            Tcl 命令字符串
        """
        if object_name:
            return f'set_property {property_name} {value} [get_{object_type} {object_name}]'
        else:
            return f'set_property {property_name} {value} [{object_type}]'
    
    @staticmethod
    def import_files_tcl(
        files: list[Path],
        fileset: str = "sources_1",
    ) -> str:
        """
        生成导入文件的 Tcl 命令（复制到项目目录）
        
        Args:
            files: 文件路径列表
            fileset: 文件集名称
            
        Returns:
            Tcl 命令字符串
        """
        file_list = ' '.join(f'"{f}"' for f in files)
        return f'import_files -fileset {fileset} {{{file_list}}}'
    
    @staticmethod
    def refresh_design_tcl() -> str:
        """
        生成刷新设计的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'update_compile_order -fileset sources_1'
    
    @staticmethod
    def set_strategy_tcl(
        step: str,
        strategy: str,
    ) -> str:
        """
        生成设置策略的 Tcl 命令
        
        Args:
            step: 步骤名称（synthesis, implementation）
            strategy: 策略名称
            
        Returns:
            Tcl 命令字符串
        """
        if step.lower() == "synthesis":
            return f'set_property strategy {strategy} [get_runs synth_1]'
        elif step.lower() == "implementation":
            return f'set_property strategy {strategy} [get_runs impl_1]'
        else:
            raise ValueError(f"未知的步骤: {step}")
    
    @staticmethod
    def export_project_tcl_tcl(
        output_path: Path,
        include_runs: bool = True,
    ) -> str:
        """
        生成导出项目为 Tcl 脚本的命令
        
        Args:
            output_path: 输出文件路径
            include_runs: 是否包含运行配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'write_project_tcl "{output_path}"'
        if include_runs:
            cmd += ' -include_runs'
        return cmd


class ProjectManager:
    """
    项目管理器
    
    提供高级的项目管理接口，结合 TclEngine 执行 Tcl 命令。
    """
    
    def __init__(self, tcl_engine):
        """
        初始化项目管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
        self.current_project: Optional[ProjectConfig] = None
    
    def create_project(
        self,
        name: str,
        path: Path,
        part: str,
        board: Optional[str] = None,
    ) -> bool:
        """
        创建新项目
        
        Args:
            name: 项目名称
            path: 项目路径
            part: 目标器件
            board: 目标开发板
            
        Returns:
            是否成功
        """
        config = ProjectConfig(
            name=name,
            path=path,
            part=part,
            board=board,
        )
        
        commands = ProjectTclGenerator.create_project_full_tcl(config)
        result = self.engine.execute(commands)
        
        if result.success:
            self.current_project = config
            logger.info(f"项目创建成功: {name}")
        else:
            logger.error(f"项目创建失败: {result.errors}")
        
        return result.success
    
    def open_project(self, path: Path) -> bool:
        """
        打开项目
        
        Args:
            path: 项目文件路径
            
        Returns:
            是否成功
        """
        command = ProjectTclGenerator.open_project_tcl(path)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"项目打开成功: {path}")
        else:
            logger.error(f"项目打开失败: {result.errors}")
        
        return result.success
    
    def close_project(self) -> bool:
        """
        关闭当前项目
        
        Returns:
            是否成功
        """
        command = ProjectTclGenerator.close_project_tcl()
        result = self.engine.execute(command)
        
        if result.success:
            self.current_project = None
            logger.info("项目已关闭")
        else:
            logger.error(f"项目关闭失败: {result.errors}")
        
        return result.success
    
    def add_sources(
        self,
        files: list[Path],
        import_files: bool = False,
    ) -> bool:
        """
        添加源文件
        
        Args:
            files: 文件列表
            import_files: 是否导入（复制）文件到项目目录
            
        Returns:
            是否成功
        """
        if import_files:
            command = ProjectTclGenerator.import_files_tcl(files, "sources_1")
        else:
            command = ProjectTclGenerator.add_source_files_tcl(files)
        
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"添加源文件成功: {len(files)} 个文件")
        else:
            logger.error(f"添加源文件失败: {result.errors}")
        
        return result.success
    
    def add_constraints(self, files: list[Path]) -> bool:
        """
        添加约束文件
        
        Args:
            files: 约束文件列表
            
        Returns:
            是否成功
        """
        command = ProjectTclGenerator.add_constraint_files_tcl(files)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"添加约束文件成功: {len(files)} 个文件")
        else:
            logger.error(f"添加约束文件失败: {result.errors}")
        
        return result.success
    
    def set_top_module(self, module: str) -> bool:
        """
        设置顶层模块
        
        Args:
            module: 模块名称
            
        Returns:
            是否成功
        """
        commands = [
            ProjectTclGenerator.set_top_module_tcl(module),
            ProjectTclGenerator.update_compile_order_tcl(),
        ]
        
        result = self.engine.execute(commands)
        
        if result.success:
            logger.info(f"顶层模块设置成功: {module}")
        else:
            logger.error(f"顶层模块设置失败: {result.errors}")
        
        return result.success
    
    def get_project_info(self) -> dict:
        """
        获取项目信息
        
        Returns:
            项目信息字典
        """
        commands = ProjectTclGenerator.get_project_info_tcl()
        result = self.engine.execute(commands)
        
        info = {}
        if result.success:
            # 解析输出获取项目信息
            for line in result.output.split('\n'):
                if line.startswith('Project:'):
                    info['name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Directory:'):
                    info['directory'] = line.split(':', 1)[1].strip()
                elif line.startswith('Part:'):
                    info['part'] = line.split(':', 1)[1].strip()
                elif line.startswith('Board:'):
                    info['board'] = line.split(':', 1)[1].strip()
                elif line.startswith('Language:'):
                    info['language'] = line.split(':', 1)[1].strip()
        
        return info
