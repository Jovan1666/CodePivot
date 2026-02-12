"""Vendor-based 配置管理与 config.json 读写"""

import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

from clients import ALL_CLIENTS, _atomic_write_json


def _get_app_dir() -> Path:
    """获取应用数据目录：打包后用 exe 所在目录，开发时用脚本目录"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


CONFIG_PATH = _get_app_dir() / "config.json"

# 三个固定厂家及其映射的客户端
VENDOR_CLIENTS = {
    "claude": ["claude_cli", "vscode"],
    "codex": ["codex"],
    "gemini": ["gemini"],
    "opencode": ["opencode"],
}

VENDOR_META = {
    "claude": {
        "display_name": "Claude",
        "subtitle": "CLI + VSCode",
        "color": "#E3000B",
        "hint": "原生: Claude Opus/Sonnet/Haiku, GLM-4.7, Qwen3, DeepSeek, Kimi K2 | 需中转: GPT/Gemini/Grok(需 LiteLLM)",
    },
    "codex": {
        "display_name": "Codex",
        "subtitle": "CLI + IDE Extension",
        "color": "#FFD700",
        "hint": "原生: gpt-5.3-codex, gpt-5.1-codex, gpt-5, o3 等 | 兼容任何 OpenAI 兼容 API (Ollama, Mistral, Azure 等)",
    },
    "gemini": {
        "display_name": "Gemini",
        "subtitle": "CLI 终端 AI 代理",
        "color": "#4285F4",
        "hint": "原生: Gemini 3 Pro/Flash | 支持 Google AI Studio API Key 或第三方中转",
    },
    "opencode": {
        "display_name": "OpenCode",
        "subtitle": "终端 AI 编程助手",
        "color": "#00852B",
        "hint": "原生: Anthropic, OpenAI, Google, 智谱等 | 通过 @ai-sdk/openai-compatible 支持任意 OpenAI 兼容 API",
    },
}

DEFAULT_CONFIG = {
    "vendors": {
        "claude": {"configs": [], "current_config_id": None},
        "codex": {"configs": [], "current_config_id": None},
        "gemini": {"configs": [], "current_config_id": None},
        "opencode": {"configs": [], "current_config_id": None},
    },
    "settings": {
        "backup_before_switch": True,
        "backup_dir": str(Path.home() / ".ai-switcher" / "backups"),
    },
}


def _load() -> dict:
    if not CONFIG_PATH.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # 兼容旧格式：自动迁移
        if "profiles" in data and "vendors" not in data:
            data = _migrate_from_profiles(data)
            _save(data)
        # 确保三个厂家都存在
        vendors = data.setdefault("vendors", {})
        for vk in VENDOR_CLIENTS:
            if vk not in vendors:
                vendors[vk] = {"configs": [], "current_config_id": None}
        return data
    except (json.JSONDecodeError, UnicodeDecodeError):
        # 配置文件损坏，备份后回退到默认配置
        _backup_corrupt_config()
        return json.loads(json.dumps(DEFAULT_CONFIG))


def _backup_corrupt_config() -> None:
    """备份损坏的 config.json 以便恢复"""
    if not CONFIG_PATH.exists():
        return
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = CONFIG_PATH.with_suffix(f".corrupt.{timestamp}.json")
        shutil.copy2(CONFIG_PATH, backup_path)
    except OSError:
        pass  # 备份失败不影响主流程


def _save(data: dict) -> None:
    _atomic_write_json(CONFIG_PATH, data)


def _migrate_from_profiles(old_data: dict) -> dict:
    """将旧 profiles 格式迁移到新 vendors 格式"""
    new_data = json.loads(json.dumps(DEFAULT_CONFIG))
    new_data["settings"] = old_data.get("settings", new_data["settings"])

    old_current = old_data.get("current_profile_id")

    for profile in old_data.get("profiles", []):
        prov = profile.get("provider", {})
        if not prov.get("api_url"):
            cli = profile.get("claude_cli", {})
            prov = {
                "api_url": cli.get("api_url", ""),
                "api_key": cli.get("api_key", ""),
                "model": cli.get("model", ""),
            }

        config_entry = {
            "id": profile.get("id", str(uuid.uuid4())),
            "name": profile.get("name", "未命名"),
            "api_url": prov.get("api_url", ""),
            "api_key": prov.get("api_key", ""),
            "model": prov.get("model", ""),
        }

        vendor_key = "claude"
        if profile.get("codex", {}).get("enabled"):
            vendor_key = "codex"
        elif profile.get("opencode", {}).get("enabled"):
            vendor_key = "opencode"

        new_data["vendors"][vendor_key]["configs"].append(config_entry)
        if profile.get("id") == old_current:
            new_data["vendors"][vendor_key]["current_config_id"] = config_entry["id"]

    return new_data


# ── 读取 ──────────────────────────────────────────

def get_vendors() -> dict:
    """返回 {vendor_key: {meta, configs, current_config_id}}"""
    data = _load()
    result = {}
    for vk, meta in VENDOR_META.items():
        vendor_data = data.get("vendors", {}).get(vk, {"configs": [], "current_config_id": None})
        result[vk] = {
            **meta,
            "configs": vendor_data.get("configs", []),
            "current_config_id": vendor_data.get("current_config_id"),
        }
    return result


# ── CRUD ──────────────────────────────────────────

def save_vendor_config(vendor: str, config_data: dict) -> dict:
    """保存/新增某厂家下的一个模型配置"""
    if vendor not in VENDOR_CLIENTS:
        raise ValueError(f"未知厂家: {vendor}")

    data = _load()
    vendor_data = data["vendors"].setdefault(vendor, {"configs": [], "current_config_id": None})
    configs = vendor_data.setdefault("configs", [])

    if config_data.get("id"):
        for i, c in enumerate(configs):
            if c["id"] == config_data["id"]:
                configs[i] = config_data
                break
        else:
            configs.append(config_data)
    else:
        config_data["id"] = str(uuid.uuid4())
        configs.append(config_data)

    _save(data)
    return config_data


def delete_vendor_config(vendor: str, config_id: str) -> bool:
    """删除某厂家下的一个模型配置"""
    data = _load()
    vendor_data = data.get("vendors", {}).get(vendor)
    if not vendor_data:
        return False

    configs = vendor_data.get("configs", [])
    new_configs = [c for c in configs if c["id"] != config_id]
    if len(new_configs) == len(configs):
        return False

    vendor_data["configs"] = new_configs
    if vendor_data.get("current_config_id") == config_id:
        vendor_data["current_config_id"] = None

    _save(data)
    return True


# ── 切换逻辑 ──────────────────────────────────────

def switch_vendor_config(vendor: str, config_id: str) -> dict:
    """切换某厂家到指定配置"""
    if vendor not in VENDOR_CLIENTS:
        return {"success": False, "message": f"未知厂家: {vendor}", "details": []}

    data = _load()
    vendor_data = data.get("vendors", {}).get(vendor, {})
    configs = vendor_data.get("configs", [])
    config = next((c for c in configs if c["id"] == config_id), None)

    if not config:
        return {"success": False, "message": "配置不存在", "details": []}

    results = []
    errors = []
    backup_before = data.get("settings", {}).get("backup_before_switch", True)
    client_keys = VENDOR_CLIENTS[vendor]

    for key in client_keys:
        client = ALL_CLIENTS.get(key)
        if not client:
            continue

        merged = _build_client_data(vendor, key, config)

        if backup_before:
            try:
                backed = client.backup()
                if backed:
                    results.append(f"[{client.display_name}] 已备份 {len(backed)} 个文件")
            except Exception as e:
                results.append(f"[{client.display_name}] 备份警告: {e}")

        try:
            client.apply(merged)
            results.append(f"[{client.display_name}] ✔ 配置已写入")
        except Exception as e:
            errors.append(f"[{client.display_name}] ✘ 写入失败: {e}")

    # 只要有客户端写入成功就更新 current_config_id（部分成功也算切换）
    has_success = any("✔" in r for r in results)
    if has_success:
        vendor_data["current_config_id"] = config_id
        _save(data)

    if errors:
        msg = "部分客户端写入失败" if has_success else "所有客户端写入失败"
        return {"success": has_success, "message": msg, "details": results + errors}

    return {
        "success": True,
        "message": f"已切换到「{config.get('name', '')}」",
        "details": results,
    }


def _build_client_data(vendor: str, client_key: str, config: dict) -> dict:
    """根据厂家和客户端，构建 client.apply() 需要的数据"""
    api_url = config.get("api_url", "")
    api_key = config.get("api_key", "")
    model = config.get("model", "")

    if client_key in ("claude_cli",):
        return {"api_url": api_url, "api_key": api_key, "model": model}

    if client_key == "vscode":
        return {"api_url": api_url, "api_key": api_key, "model": model}

    if client_key == "codex":
        return {
            "api_key": api_key,
            "base_url": api_url,
            "model": model,
            "provider_name": config.get("provider_name", "custom"),
            "reasoning_effort": config.get("reasoning_effort", "high"),
        }

    if client_key == "gemini":
        return {
            "api_key": api_key,
            "base_url": api_url,
            "model": model,
        }

    if client_key == "opencode":
        model_name = config.get("model_name", "") or model
        # 防止空 model_name 导致 OpenCode 配置中出现空 key
        models = {}
        if model_name:
            models[model_name] = {
                "name": config.get("display_name", "") or model_name,
                "limit": {
                    "context": config.get("context_limit", 200000),
                    "output": config.get("output_limit", 64000),
                },
            }
        return {
            "api_key": api_key,
            "base_url": api_url,
            "provider_id": config.get("provider_id", "anthropic"),
            "npm": config.get("npm", ""),
            "display_name": config.get("display_name", ""),
            "models": models,
        }

    return {}


# ── 客户端检测 ────────────────────────────────────

def detect_clients() -> dict[str, bool]:
    return {key: client.detect() for key, client in ALL_CLIENTS.items()}
