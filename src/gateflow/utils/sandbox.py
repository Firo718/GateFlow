"""
文件系统沙箱安全模块。

提供路径校验和访问控制，防止 AI 代理越权访问、误删关键文件等高风险操作。

主要功能：
- 定义沙箱根目录白名单
- 路径校验，确保操作在允许的范围内
- 危险操作保护机制
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SandboxConfig:
    """
    沙箱配置管理器。
    
    管理允许访问的根目录列表，支持通过环境变量或配置文件设置。
    
    注意：现在配置由 gateflow.settings 模块统一管理。
    SandboxConfig 保留用于向后兼容，但内部使用 GateFlowSettings。
    
    Example:
        ```python
        # 使用默认配置（从 settings 读取）
        config = SandboxConfig()
        
        # 自定义根目录
        config = SandboxConfig(allowed_roots=["/home/user/projects"])
        
        # 从 settings 创建（推荐）
        from gateflow.settings import get_settings
        settings = get_settings()
        config = SandboxConfig.from_settings(settings)
        ```
    """
    
    # 默认沙箱根目录
    DEFAULT_WORKSPACE_ROOT = Path.home() / ".gateflow" / "workspaces"
    
    def __init__(
        self,
        allowed_roots: list[str] | None = None,
        allow_dangerous_operations: bool | None = None,
    ):
        """
        初始化沙箱配置。
        
        Args:
            allowed_roots: 允许访问的根目录列表，None 则从 settings 读取
            allow_dangerous_operations: 是否允许危险操作，None 则从 settings 读取
        """
        settings = None
        if allowed_roots is None or allow_dangerous_operations is None:
            # 仅在需要默认值时读取 settings，避免环境变量格式不兼容导致初始化失败
            try:
                from gateflow.settings import get_settings

                settings = get_settings()
            except Exception as exc:  # pragma: no cover - 防御性分支
                logger.warning(f"读取 settings 失败，回退到 Sandbox 默认值: {exc}")
        
        self._allowed_roots: list[Path] = []
        
        # 设置危险操作开关
        if allow_dangerous_operations is None:
            self.allow_dangerous_operations = (
                settings.allow_dangerous_operations if settings is not None else False
            )
        else:
            self.allow_dangerous_operations = allow_dangerous_operations
        
        if allowed_roots:
            # 使用用户指定的根目录
            for root in allowed_roots:
                root_path = Path(root).resolve()
                if root_path not in self._allowed_roots:
                    self._allowed_roots.append(root_path)
        else:
            # 从 settings 读取工作空间根目录
            if settings is not None:
                workspace_roots = settings.get_workspace_roots()
                for root in workspace_roots:
                    root_path = root.resolve()
                    if root_path not in self._allowed_roots:
                        self._allowed_roots.append(root_path)
            
            # 如果 settings 中没有配置，使用默认目录
            if not self._allowed_roots:
                default_root = self.DEFAULT_WORKSPACE_ROOT.resolve()
                self._allowed_roots.append(default_root)
            
            # 尝试添加当前工作目录
            try:
                cwd = Path.cwd().resolve()
                if cwd not in self._allowed_roots:
                    self._allowed_roots.append(cwd)
            except Exception:
                pass
        
        # 确保默认工作空间目录存在
        self._ensure_default_workspace()
        
        logger.info(f"沙箱配置初始化: 允许的根目录 = {[str(r) for r in self._allowed_roots]}")
    
    @classmethod
    def from_settings(cls, settings: Any) -> "SandboxConfig":
        """
        从 GateFlowSettings 创建配置。
        
        Args:
            settings: GateFlowSettings 实例
        
        Returns:
            SandboxConfig 实例
        """
        return cls(
            allowed_roots=settings.workspace_roots if settings.workspace_roots else None,
            allow_dangerous_operations=settings.allow_dangerous_operations,
        )
    
    @classmethod
    def from_env(cls) -> "SandboxConfig":
        """
        从环境变量创建配置（现在从 settings 读取）。
        
        环境变量由 GateFlowSettings 统一管理:
            GATEFLOW_WORKSPACE_ROOTS: 用路径分隔符分隔的根目录列表
            GATEFLOW_ALLOW_DANGEROUS: 是否允许危险操作 (true/false)
        
        Returns:
            SandboxConfig 实例
        """
        roots_env = os.environ.get("GATEFLOW_WORKSPACE_ROOTS")
        dangerous_env = os.environ.get("GATEFLOW_ALLOW_DANGEROUS")

        allowed_roots: list[str] | None = None
        if roots_env:
            allowed_roots = [root.strip() for root in roots_env.split(os.pathsep) if root.strip()]

        allow_dangerous_operations: bool | None = None
        if dangerous_env is not None:
            allow_dangerous_operations = dangerous_env.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        return cls(
            allowed_roots=allowed_roots,
            allow_dangerous_operations=allow_dangerous_operations,
        )
    
    def _ensure_default_workspace(self) -> None:
        """确保默认工作空间目录存在"""
        try:
            for root in self._allowed_roots:
                if not root.exists():
                    root.mkdir(parents=True, exist_ok=True)
                    logger.info(f"创建工作空间目录: {root}")
        except Exception as e:
            logger.warning(f"无法创建默认工作空间目录: {e}")
    
    @property
    def allowed_roots(self) -> list[Path]:
        """获取允许的根目录列表"""
        return self._allowed_roots.copy()
    
    def add_root(self, root: str | Path) -> None:
        """
        添加允许的根目录。
        
        Args:
            root: 根目录路径
        """
        root_path = Path(root).resolve()
        if root_path not in self._allowed_roots:
            self._allowed_roots.append(root_path)
            logger.info(f"添加沙箱根目录: {root_path}")
    
    def remove_root(self, root: str | Path) -> None:
        """
        移除允许的根目录。
        
        Args:
            root: 根目录路径
        """
        root_path = Path(root).resolve()
        if root_path in self._allowed_roots:
            self._allowed_roots.remove(root_path)
            logger.info(f"移除沙箱根目录: {root_path}")
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "allowed_roots": [str(r) for r in self._allowed_roots],
            "allow_dangerous_operations": self.allow_dangerous_operations,
        }


def validate_path(
    path: str | Path,
    allowed_roots: list[str | Path],
    must_exist: bool = False,
) -> tuple[bool, str]:
    """
    校验路径是否在允许的根目录下。
    
    Args:
        path: 要校验的路径
        allowed_roots: 允许的根目录列表
        must_exist: 是否要求路径必须存在
    
    Returns:
        (is_valid, error_message)
        - is_valid: 路径是否有效
        - error_message: 错误信息（如果无效）
    
    Example:
        ```python
        is_valid, error = validate_path(
            "/home/user/projects/file.txt",
            ["/home/user/projects"]
        )
        if not is_valid:
            print(error)
        ```
    """
    try:
        # 解析路径
        target_path = Path(path).resolve()
        
        # 检查路径是否存在（如果要求）
        if must_exist and not target_path.exists():
            return False, f"路径 '{path}' 不存在"
        
        # 检查是否在允许的根目录下
        for root in allowed_roots:
            root_path = Path(root).resolve()
            
            # 检查目标路径是否在根目录下
            try:
                # 使用 relative_to 检查是否为子路径
                target_path.relative_to(root_path)
                return True, ""
            except ValueError:
                # 不在当前根目录下，继续检查下一个
                continue
        
        # 所有根目录都不匹配
        roots_str = "\n  - ".join(str(r) for r in allowed_roots)
        error_msg = (
            f"路径 '{path}' 不在允许的沙箱范围内。\n"
            f"允许的根目录:\n  - {roots_str}\n\n"
            f"解决方法:\n"
            f"1. 将路径移动到允许的目录下\n"
            f"2. 通过环境变量 GATEFLOW_WORKSPACE_ROOTS 添加新的根目录\n"
            f"   例如: export GATEFLOW_WORKSPACE_ROOTS=\"/path1:/path2\"\n"
            f"3. 或在代码中调用 sandbox_config.add_root('/your/path')"
        )
        return False, error_msg
        
    except Exception as e:
        return False, f"路径校验失败: {str(e)}"


def validate_path_for_read(
    path: str | Path,
    allowed_roots: list[str | Path],
) -> tuple[bool, str]:
    """
    校验读取路径。
    
    Args:
        path: 要读取的路径
        allowed_roots: 允许的根目录列表
    
    Returns:
        (is_valid, error_message)
    """
    return validate_path(path, allowed_roots, must_exist=True)


def validate_path_for_write(
    path: str | Path,
    allowed_roots: list[str | Path],
) -> tuple[bool, str]:
    """
    校验写入路径。
    
    Args:
        path: 要写入的路径
        allowed_roots: 允许的根目录列表
    
    Returns:
        (is_valid, error_message)
    """
    # 写入路径不需要必须存在（可能会创建新文件）
    return validate_path(path, allowed_roots, must_exist=False)


def validate_path_for_delete(
    path: str | Path,
    allowed_roots: list[str | Path],
    allow_dangerous: bool = False,
) -> tuple[bool, str]:
    """
    校验删除路径。
    
    删除操作需要显式的危险操作开关。
    
    Args:
        path: 要删除的路径
        allowed_roots: 允许的根目录列表
        allow_dangerous: 是否允许危险操作
    
    Returns:
        (is_valid, error_message)
    """
    # 检查危险操作开关
    if not allow_dangerous:
        return False, (
            f"删除操作需要显式启用危险操作开关。\n\n"
            f"解决方法:\n"
            f"1. 通过环境变量启用: export GATEFLOW_ALLOW_DANGEROUS=true\n"
            f"2. 或在配置中设置: sandbox_config.allow_dangerous_operations = True\n"
            f"3. 或在工具调用时传递 allow_dangerous=True 参数\n\n"
            f"警告: 删除操作不可恢复，请谨慎使用！"
        )
    
    # 检查路径是否在沙箱内
    return validate_path(path, allowed_roots, must_exist=True)


# 全局默认沙箱配置
_default_config: SandboxConfig | None = None


def get_default_config() -> SandboxConfig:
    """
    获取默认沙箱配置。
    
    如果未初始化，会自动从环境变量创建配置。
    
    Returns:
        SandboxConfig 实例
    """
    global _default_config
    
    if _default_config is None:
        _default_config = SandboxConfig.from_env()
    
    return _default_config


def set_default_config(config: SandboxConfig) -> None:
    """
    设置默认沙箱配置。
    
    Args:
        config: SandboxConfig 实例
    """
    global _default_config
    _default_config = config
    logger.info("已更新默认沙箱配置")
