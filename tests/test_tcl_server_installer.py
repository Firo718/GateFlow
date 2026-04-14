"""
TclServerInstaller 安装/卸载逻辑测试
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gateflow.vivado.tcl_server import (
    DEFAULT_PORT,
    TCL_SERVER_TEMPLATE,
    TclServerInstaller,
    VivadoInstallation,
)


@pytest.fixture
def mock_vivado_installation(tmp_path):
    """创建模拟的 Vivado 安装信息"""
    vivado_path = tmp_path / "Vivado" / "2024.1"
    vivado_path.mkdir(parents=True)
    
    # 创建 bin 目录和可执行文件
    bin_path = vivado_path / "bin"
    bin_path.mkdir()
    (bin_path / "vivado.bat").touch()
    
    # 创建 init_tcl 路径（用户配置目录）
    init_tcl_path = tmp_path / "AppData" / "Xilinx" / "Vivado" / "Vivado_init.tcl"
    
    return VivadoInstallation(
        version="2024.1",
        path=vivado_path,
        executable=bin_path / "vivado.bat",
        init_tcl_path=init_tcl_path,
    )


class TestTclServerInstallerGenerateScript:
    """测试 generate_script 方法"""

    def test_generate_script_default_port(self):
        """测试生成默认端口的脚本"""
        installer = TclServerInstaller()
        script = installer.generate_script()
        
        assert "GateFlow Tcl Server" in script
        assert str(DEFAULT_PORT) in script
        assert "gateflow_accept_connection" in script
        assert "gateflow_handle_client" in script
        assert "gateflow_start_server" in script
        assert "vwait forever" in script

    def test_generate_script_custom_port(self):
        """测试生成自定义端口的脚本"""
        installer = TclServerInstaller()
        script = installer.generate_script(port=8888)
        
        assert "8888" in script
        assert "GateFlow Tcl Server" in script

    def test_generate_script_non_blocking_for_vivado_init(self):
        """Vivado_init.tcl 注入脚本不应阻塞 GUI 启动"""
        installer = TclServerInstaller()
        script = installer.generate_script(port=9999, blocking=False)

        assert "gateflow_start_server 9999" in script
        assert "vwait forever" not in script

    def test_generate_script_with_version(self):
        """测试生成带版本号的脚本"""
        installer = TclServerInstaller()
        script = installer.generate_script(port=9999, version="2.0")
        
        assert "Version: 2.0" in script

    def test_script_has_marker_comments(self):
        """测试脚本包含必要的注释"""
        installer = TclServerInstaller()
        script = installer.generate_script()
        
        assert "UTF-8" in script
        assert "TCP" in script

    def test_script_has_error_handling(self):
        """测试脚本包含错误处理"""
        installer = TclServerInstaller()
        script = installer.generate_script()
        
        assert "ERROR:" in script
        assert "catch" in script


class TestTclServerInstallerInstall:
    """测试安装逻辑"""

    def test_install_creates_init_tcl(self, mock_vivado_installation):
        """测试安装时创建 Vivado_init.tcl"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 安装
        result = installer.install(port=9999)
        
        assert result is True
        assert mock_vivado_installation.init_tcl_path.exists()

    def test_install_adds_marker_blocks(self, mock_vivado_installation):
        """测试安装时添加标记块"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        result = installer.install(port=9999)
        
        assert result is True
        
        # 读取文件内容
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        assert TclServerInstaller.GATEFLOW_MARKER_START in content
        assert TclServerInstaller.GATEFLOW_MARKER_END in content

    def test_install_injects_non_blocking_script(self, mock_vivado_installation):
        """安装到 Vivado_init.tcl 时不应写入阻塞事件循环"""
        installer = TclServerInstaller(mock_vivado_installation)

        result = installer.install(port=9999)

        assert result is True
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        assert "gateflow_start_server 9999" in content
        assert "vwait forever" not in content

    def test_install_idempotent(self, mock_vivado_installation):
        """测试重复安装不会破坏文件"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 第一次安装
        result1 = installer.install(port=9999)
        assert result1 is True
        
        # 读取内容
        content1 = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 第二次安装
        result2 = installer.install(port=8888)
        assert result2 is True
        
        # 读取内容
        content2 = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 确保只有一个标记块
        assert content2.count(TclServerInstaller.GATEFLOW_MARKER_START) == 1
        assert content2.count(TclServerInstaller.GATEFLOW_MARKER_END) == 1
        
        # 确保端口已更新
        assert "8888" in content2

    def test_install_preserves_existing_content(self, mock_vivado_installation):
        """测试安装时保留现有内容"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 创建现有的 init.tcl
        mock_vivado_installation.init_tcl_path.parent.mkdir(parents=True, exist_ok=True)
        existing_content = "# Existing Vivado config\nset my_var 123\n"
        mock_vivado_installation.init_tcl_path.write_text(existing_content, encoding='utf-8')
        
        # 安装
        result = installer.install(port=9999)
        assert result is True
        
        # 读取内容
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 确保现有内容被保留
        assert "# Existing Vivado config" in content
        assert "set my_var 123" in content


class TestTclServerInstallerUninstall:
    """测试卸载逻辑"""

    def test_uninstall_removes_marker_blocks(self, mock_vivado_installation):
        """测试卸载时移除标记块"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 先安装
        installer.install(port=9999)
        
        # 确认已安装
        assert installer.is_installed()
        
        # 卸载
        result = installer.uninstall()
        assert result is True
        
        # 读取内容
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 确保标记块已移除
        assert TclServerInstaller.GATEFLOW_MARKER_START not in content
        assert TclServerInstaller.GATEFLOW_MARKER_END not in content

    def test_uninstall_idempotent(self, mock_vivado_installation):
        """测试重复卸载不会出错"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 安装
        installer.install(port=9999)
        
        # 第一次卸载
        result1 = installer.uninstall()
        assert result1 is True
        
        # 第二次卸载（应该返回 True，因为已经卸载）
        result2 = installer.uninstall()
        assert result2 is True

    def test_uninstall_preserves_existing_content(self, mock_vivado_installation):
        """测试卸载时保留现有内容"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 创建现有的 init.tcl
        mock_vivado_installation.init_tcl_path.parent.mkdir(parents=True, exist_ok=True)
        existing_content = "# Existing Vivado config\nset my_var 123\n"
        mock_vivado_installation.init_tcl_path.write_text(existing_content, encoding='utf-8')
        
        # 安装
        installer.install(port=9999)
        
        # 卸载
        result = installer.uninstall()
        assert result is True
        
        # 读取内容
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 确保现有内容被保留
        assert "# Existing Vivado config" in content
        assert "set my_var 123" in content

    def test_uninstall_non_existent_file(self, mock_vivado_installation):
        """测试卸载不存在的文件"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 不创建文件，直接卸载
        result = installer.uninstall()
        assert result is True


class TestTclServerInstallerIsInstalled:
    """测试 is_installed 方法"""

    def test_is_installed_false_initially(self, mock_vivado_installation):
        """测试初始状态未安装"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        assert installer.is_installed() is False

    def test_is_installed_true_after_install(self, mock_vivado_installation):
        """测试安装后状态为已安装"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        installer.install(port=9999)
        
        assert installer.is_installed() is True

    def test_is_installed_false_after_uninstall(self, mock_vivado_installation):
        """测试卸载后状态为未安装"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        installer.install(port=9999)
        installer.uninstall()
        
        assert installer.is_installed() is False


class TestTclServerInstallerInstallToVivado:
    """测试 install_to_vivado 方法"""

    def test_install_to_vivado_with_vivado_info(self, mock_vivado_installation):
        """测试有 Vivado 信息时安装"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        result = installer.install_to_vivado(port=9999)
        
        assert result is True

    def test_install_to_vivado_without_vivado_info(self):
        """测试无 Vivado 信息时安装"""
        installer = TclServerInstaller(None)
        
        result = installer.install_to_vivado(port=9999)
        
        assert result is False


class TestTclServerInstallerUninstallFromVivado:
    """测试 uninstall_from_vivado 方法"""

    def test_uninstall_from_vivado_with_vivado_info(self, mock_vivado_installation):
        """测试有 Vivado 信息时卸载"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 先安装
        installer.install_to_vivado(port=9999)
        
        # 卸载
        result = installer.uninstall_from_vivado()
        
        assert result is True

    def test_uninstall_from_vivado_without_vivado_info(self):
        """测试无 Vivado 信息时卸载"""
        installer = TclServerInstaller(None)
        
        result = installer.uninstall_from_vivado()
        
        assert result is False


class TestMarkerBlockMechanism:
    """测试标记块机制"""

    def test_marker_format(self):
        """测试标记块格式"""
        assert "BEGIN" in TclServerInstaller.GATEFLOW_MARKER_START
        assert "END" in TclServerInstaller.GATEFLOW_MARKER_END
        assert "GateFlow" in TclServerInstaller.GATEFLOW_MARKER_START
        assert "GateFlow" in TclServerInstaller.GATEFLOW_MARKER_END

    def test_marker_uniqueness(self, mock_vivado_installation):
        """测试标记块唯一性"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 多次安装
        installer.install(port=9999)
        installer.install(port=8888)
        installer.install(port=7777)
        
        # 读取内容
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 确保只有一个标记块
        assert content.count(TclServerInstaller.GATEFLOW_MARKER_START) == 1
        assert content.count(TclServerInstaller.GATEFLOW_MARKER_END) == 1

    def test_marker_clean_removal(self, mock_vivado_installation):
        """测试标记块干净移除"""
        installer = TclServerInstaller(mock_vivado_installation)
        
        # 创建现有的 init.tcl
        mock_vivado_installation.init_tcl_path.parent.mkdir(parents=True, exist_ok=True)
        existing_content = "# Before\nset a 1\n# After\n"
        mock_vivado_installation.init_tcl_path.write_text(existing_content, encoding='utf-8')
        
        # 安装
        installer.install(port=9999)
        
        # 卸载
        installer.uninstall()
        
        # 读取内容
        content = mock_vivado_installation.init_tcl_path.read_text(encoding='utf-8')
        
        # 确保没有多余的空行
        assert "\n\n\n" not in content
