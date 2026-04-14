"""
路径转换功能演示

演示如何使用路径工具模块自动转换 Windows 路径为 Tcl 格式。
"""

from gateflow.utils.path_utils import (
    to_tcl_path,
    to_windows_path,
    normalize_path,
    convert_dict_paths,
    PathConverter,
)


def demo_basic_conversion():
    """演示基本路径转换"""
    print("=" * 60)
    print("基本路径转换演示")
    print("=" * 60)
    
    # Windows 路径转换
    windows_path = r"C:\Users\project\src\top.v"
    tcl_path = to_tcl_path(windows_path)
    print(f"Windows 路径: {windows_path}")
    print(f"Tcl 路径:     {tcl_path}")
    print()
    
    # 混合斜杠路径
    mixed_path = r"D:\Xilinx/Vivado\project"
    converted = to_tcl_path(mixed_path)
    print(f"混合斜杠路径: {mixed_path}")
    print(f"转换后:       {converted}")
    print()


def demo_normalize_path():
    """演示路径规范化"""
    print("=" * 60)
    print("路径规范化演示")
    print("=" * 60)
    
    # 相对路径规范化
    relative_path = ".\\project\\src"
    normalized = normalize_path(relative_path)
    print(f"相对路径: {relative_path}")
    print(f"规范化:  {normalized}")
    print()


def demo_dict_conversion():
    """演示字典路径转换"""
    print("=" * 60)
    print("字典路径转换演示")
    print("=" * 60)
    
    # 项目配置字典
    config = {
        "name": "my_project",
        "path": r"C:\Projects\FPGA\my_project",
        "output_dir": r"D:\Output\bitstream",
        "source_dir": r"C:\Projects\Sources",
        "files": [
            r"C:\src\top.v",
            r"D:\ip\core.xci",
        ],
        "settings": {
            "vivado_path": r"C:\Xilinx\Vivado\2023.1",
            "working_dir": r"D:\temp\work",
        },
    }
    
    print("原始配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()
    
    # 转换字典中的路径
    converted = convert_dict_paths(config)
    
    print("转换后配置:")
    for key, value in converted.items():
        print(f"  {key}: {value}")
    print()


def demo_command_conversion():
    """演示命令中的路径转换"""
    print("=" * 60)
    print("Tcl 命令路径转换演示")
    print("=" * 60)
    
    # 原始命令（包含 Windows 路径）
    commands = [
        r'create_project "my_proj" "C:\Users\project\my_proj" -part xc7a35t',
        r'add_files "C:\src\top.v" "D:\ip\core.xci"',
        r'open_project {D:\Projects\test\test.xpr}',
    ]
    
    for cmd in commands:
        print(f"原始命令: {cmd}")
        converted = PathConverter.convert_paths_in_command(cmd)
        print(f"转换后:   {converted}")
        print()


def demo_path_detection():
    """演示路径检测"""
    print("=" * 60)
    print("路径类型检测演示")
    print("=" * 60)
    
    paths = [
        r"C:\Users\project",
        "C:/Users/project",
        "/home/user/project",
        r"\\server\share\folder",
    ]
    
    for path in paths:
        is_tcl = PathConverter.is_tcl_path(path)
        is_windows = PathConverter.is_windows_path(path)
        print(f"路径: {path}")
        print(f"  Tcl 格式:     {is_tcl}")
        print(f"  Windows 格式: {is_windows}")
        print()


def main():
    """主函数"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "GateFlow 路径转换功能演示" + " " * 22 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    demo_basic_conversion()
    demo_normalize_path()
    demo_dict_conversion()
    demo_command_conversion()
    demo_path_detection()
    
    print("=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
