"""暴露给前端的 PyWebView API"""

import subprocess
import traceback
import config_manager as cm
import env_manager as ev


# 最低版本要求（根据官方文档和已知问题设定）
MIN_VERSIONS = {
    "claude": "0.2.0",  # Claude Code CLI v0.2.0+ 支持中转配置
    "codex": "0.4.0",  # Codex CLI v0.4.0+ 移除 wire_api，仅支持 responses
    "gemini": "0.3.0",  # Gemini CLI v0.3.0+ 使用新 settings.json 格式
    "opencode": "1.0.0",  # OpenCode v1.0.0+ 要求 models 字段
}


def _check_version(command: str, min_version: str) -> tuple[bool, str, str]:
    """检测客户端版本，返回 (是否满足最低版本, 当前版本, 提示信息)"""
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="ignore",
        )
        if result.returncode != 0:
            return False, "未知", f"无法检测 {command} 版本"

        # 解析版本号（不同 CLI 输出格式不同）
        output = result.stdout.strip() or result.stderr.strip()
        version = output.split()[-1] if output else "未知"

        # 简单版本比较（只比较主版本号）
        current_parts = version.replace("v", "").split(".")
        min_parts = min_version.split(".")

        is_compatible = True
        for i in range(min(len(current_parts), len(min_parts))):
            try:
                if int(current_parts[i]) < int(min_parts[i]):
                    is_compatible = False
                    break
                elif int(current_parts[i]) > int(min_parts[i]):
                    break
            except ValueError:
                continue

        if not is_compatible:
            return (
                False,
                version,
                f"当前版本 {version} 低于推荐的 {min_version}，请升级以获得最佳兼容性",
            )

        return True, version, f"版本 {version} 兼容"

    except FileNotFoundError:
        return False, "未安装", f"未检测到 {command}，请先安装"
    except Exception as e:
        return False, "检测失败", str(e)


def _safe_call(func, *args, error_return=None):
    """包装调用，捕获异常返回友好提示而不是原始 traceback"""
    try:
        return func(*args)
    except Exception as e:
        traceback.print_exc()  # 服务端日志保留完整堆栈
        if error_return == "dict":
            return {"success": False, "message": f"操作失败: {e}", "details": []}
        raise RuntimeError(str(e))  # 返回简洁错误信息给前端


class Api:
    """PyWebView API — 前端通过 window.pywebview.api.xxx() 调用"""

    def get_vendors(self) -> dict:
        return _safe_call(cm.get_vendors)

    def save_vendor_config(self, vendor: str, config_data: dict) -> dict:
        return _safe_call(cm.save_vendor_config, vendor, config_data)

    def delete_vendor_config(self, vendor: str, config_id: str) -> bool:
        return _safe_call(cm.delete_vendor_config, vendor, config_id)

    def switch_vendor_config(self, vendor: str, config_id: str) -> dict:
        """切换配置并同时部署到环境变量"""
        # 1. 先切换配置文件
        result = _safe_call(
            cm.switch_vendor_config, vendor, config_id, error_return="dict"
        )

        # 2. 如果配置文件切换成功，同时部署到环境变量
        if result.get("success"):
            try:
                cfg = cm.get_current_config(vendor)
                if cfg and cfg.get("id") == config_id:
                    env_result = ev.deploy_to_env_vars(vendor, cfg)
                    result["env_deploy"] = env_result
            except Exception as e:
                # 环境变量部署失败不影响配置文件切换的成功状态
                result["env_deploy"] = {
                    "success": False,
                    "message": f"环境变量部署失败: {e}",
                    "set_vars": [],
                    "failed_vars": [],
                }

        return result

    def detect_clients(self) -> dict:
        return _safe_call(cm.detect_clients)

    def deploy_to_env_vars(self, vendor: str, config_id: str) -> dict:
        """将配置部署到系统环境变量"""
        return _safe_call(
            self._deploy_to_env_vars_impl, vendor, config_id, error_return="dict"
        )

    def _deploy_to_env_vars_impl(self, vendor: str, config_id: str) -> dict:
        """部署环境变量的实际实现"""
        cfg = cm.get_current_config(vendor)
        if not cfg or cfg.get("id") != config_id:
            return {
                "success": False,
                "message": "请先切换到此配置",
                "set_vars": [],
                "failed_vars": [],
            }
        return ev.deploy_to_env_vars(vendor, cfg)

    def env_vars_status(self, vendor: str) -> dict:
        """获取环境变量状态"""
        return _safe_call(ev.get_env_vars_status, vendor)

    def remove_env_vars(self, vendor: str) -> dict:
        """清除环境变量"""
        return _safe_call(ev.remove_env_vars, vendor, error_return="dict")

    def check_vendor_versions(self) -> dict:
        """检测各厂商 CLI 版本兼容性（并行执行）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}
        vendors = [
            ("claude", "claude"),
            ("codex", "codex"),
            ("gemini", "gemini"),
            ("opencode", "opencode"),
        ]

        # 使用线程池并行检测版本，避免顺序执行阻塞
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_vendor = {
                executor.submit(_check_version, cmd, MIN_VERSIONS[vendor]): vendor
                for vendor, cmd in vendors
            }

            for future in as_completed(future_to_vendor):
                vendor = future_to_vendor[future]
                try:
                    results[vendor] = future.result()
                except Exception as e:
                    results[vendor] = (False, "检测失败", str(e))

        return results

    def get_min_versions(self) -> dict:
        """获取推荐的最低版本要求"""
        return MIN_VERSIONS
