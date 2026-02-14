"""环境变量管理模块 - 处理系统环境变量的部署"""

import ctypes
import json
import os
import subprocess
from pathlib import Path

# 环境变量到厂商的映射
VENDOR_ENV_MAP = {
    "claude": ["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"],
    "codex": ["OPENAI_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_GEMINI_BASE_URL"],
    "opencode": ["OPNCODE_API_KEY", "OPNCODE_BASE_URL"],
}


def _is_admin() -> bool:
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def _escape_powershell_string(s: str) -> str:
    """转义 PowerShell 单引号字符串中的特殊字符"""
    # 单引号字符串中唯一需要转义的是单引号本身，用两个单引号表示
    return s.replace("'", "''")


def _set_system_env_var(name: str, value: str) -> bool:
    """设置系统环境变量（需要管理员权限）"""
    try:
        # 使用单引号防止 PowerShell 变量展开和命令注入
        safe_name = _escape_powershell_string(name)
        safe_value = _escape_powershell_string(value)
        cmd = f"[Environment]::SetEnvironmentVariable('{safe_name}', '{safe_value}', 'User')"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _remove_system_env_var(name: str) -> bool:
    """删除系统环境变量（传 $null 真正删除，而非设为空字符串）"""
    try:
        safe_name = _escape_powershell_string(name)
        cmd = f"[Environment]::SetEnvironmentVariable('{safe_name}', $null, 'User')"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def deploy_to_env_vars(vendor: str, profile_data: dict) -> dict:
    """
    将配置部署到系统环境变量

    Args:
        vendor: 厂商标识 (claude/codex/gemini/opencode)
        profile_data: 配置数据

    Returns:
        dict: {"success": bool, "message": str, "set_vars": list, "failed_vars": list}
    """
    if vendor not in VENDOR_ENV_MAP:
        return {
            "success": False,
            "message": f"不支持的厂商: {vendor}",
            "set_vars": [],
            "failed_vars": [],
        }

    env_vars = VENDOR_ENV_MAP[vendor]
    set_vars = []
    failed_vars = []

    # 根据厂商构建环境变量映射
    if vendor == "claude":
        mappings = {
            "ANTHROPIC_AUTH_TOKEN": profile_data.get("api_key", ""),
            "ANTHROPIC_BASE_URL": profile_data.get("api_url", ""),
            "ANTHROPIC_MODEL": profile_data.get("model", ""),
        }
    elif vendor == "codex":
        mappings = {
            "OPENAI_API_KEY": profile_data.get("api_key", ""),
        }
    elif vendor == "gemini":
        mappings = {
            "GEMINI_API_KEY": profile_data.get("api_key", ""),
            "GOOGLE_GEMINI_BASE_URL": profile_data.get("base_url", ""),
        }
    elif vendor == "opencode":
        mappings = {
            "OPNCODE_API_KEY": profile_data.get("api_key", ""),
            "OPNCODE_BASE_URL": profile_data.get("base_url", ""),
        }
    else:
        mappings = {}

    # 设置环境变量
    for var_name, var_value in mappings.items():
        if var_value:  # 只设置有值的变量
            if _set_system_env_var(var_name, var_value):
                set_vars.append(var_name)
            else:
                failed_vars.append(var_name)

    success = len(failed_vars) == 0
    message = (
        f"成功设置 {len(set_vars)} 个环境变量"
        if success
        else f"部分失败: {len(set_vars)} 成功, {len(failed_vars)} 失败"
    )

    return {
        "success": success,
        "message": message,
        "set_vars": set_vars,
        "failed_vars": failed_vars,
    }


def _get_registry_env_var(name: str) -> str:
    """从注册表读取用户级环境变量的真实值（而非当前进程快照）"""
    try:
        safe_name = _escape_powershell_string(name)
        cmd = f"[Environment]::GetEnvironmentVariable('{safe_name}', 'User')"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return ""
    except Exception:
        return ""


def get_env_vars_status(vendor: str) -> dict:
    """
    获取环境变量当前状态（从注册表读取，确保与 deploy 结果一致）

    Args:
        vendor: 厂商标识

    Returns:
        dict: 各环境变量的值（为空表示未设置）
    """
    if vendor not in VENDOR_ENV_MAP:
        return {}

    result = {}
    for var_name in VENDOR_ENV_MAP[vendor]:
        result[var_name] = _get_registry_env_var(var_name)

    return result


def remove_env_vars(vendor: str) -> dict:
    """
    清除指定厂商的环境变量

    Args:
        vendor: 厂商标识

    Returns:
        dict: {"success": bool, "message": str, "removed_vars": list}
    """
    if vendor not in VENDOR_ENV_MAP:
        return {
            "success": False,
            "message": f"不支持的厂商: {vendor}",
            "removed_vars": [],
        }

    removed_vars = []
    for var_name in VENDOR_ENV_MAP[vendor]:
        if _get_registry_env_var(var_name):
            if _remove_system_env_var(var_name):
                removed_vars.append(var_name)

    return {
        "success": True,
        "message": f"已清除 {len(removed_vars)} 个环境变量",
        "removed_vars": removed_vars,
    }


def generate_batch_script(
    vendor: str, profile_data: dict, output_path: Path = None
) -> Path:
    """
    生成批处理脚本，包含设置环境变量的命令

    Args:
        vendor: 厂商标识
        profile_data: 配置数据
        output_path: 输出脚本路径，默认为项目根目录下的 set_env.bat

    Returns:
        Path: 生成的脚本路径
    """
    if output_path is None:
        output_path = Path(__file__).parent / "temp_env.bat"

    # 根据厂商生成环境变量设置命令
    lines = ["@echo off", "echo 设置环境变量...", ""]

    if vendor == "claude":
        if profile_data.get("api_key"):
            lines.append(f"set ANTHROPIC_AUTH_TOKEN={profile_data['api_key']}")
        if profile_data.get("api_url"):
            lines.append(f"set ANTHROPIC_BASE_URL={profile_data['api_url']}")
        if profile_data.get("model"):
            lines.append(f"set ANTHROPIC_MODEL={profile_data['model']}")
        lines.append("")
        lines.append("echo 启动 Claude CLI...")
        lines.append("claude")
    elif vendor == "codex":
        if profile_data.get("api_key"):
            lines.append(f"set OPENAI_API_KEY={profile_data['api_key']}")
        lines.append("")
        lines.append("echo 启动 Codex CLI...")
        lines.append("codex")
    lines.append("")
    lines.append("pause")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
