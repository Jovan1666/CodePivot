"""AI 编程客户端的配置写入逻辑"""

import json
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

# 备份根目录
BACKUP_DIR = Path.home() / ".ai-switcher" / "backups"
MAX_BACKUPS = 10


# ── 原子写入工具 ──────────────────────────────

def _atomic_write_text(path: Path, content: str) -> None:
    """原子写入文本文件：先写临时文件再 rename，避免写入中断导致文件损坏"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # os.replace 在所有平台上都能原子替换已存在的目标文件
        os.replace(tmp_path, str(path))
    except Exception:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _atomic_write_json(path: Path, data: dict) -> None:
    """原子写入 JSON 文件"""
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))


class ClientBase(ABC):
    """客户端配置写入基类"""

    @property
    @abstractmethod
    def config_paths(self) -> list[Path]:
        """需要写入的配置文件路径列表"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """客户端显示名称"""

    def backup(self) -> list[str]:
        """备份当前配置文件，返回备份路径列表"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backed_up = []
        for path in self.config_paths:
            if path.exists():
                backup_name = f"{self.display_name}_{path.name}_{timestamp}"
                backup_path = BACKUP_DIR / backup_name
                shutil.copy2(path, backup_path)
                backed_up.append(str(backup_path))
        self._cleanup_old_backups()
        return backed_up

    def _cleanup_old_backups(self):
        """保留最近 MAX_BACKUPS 份备份"""
        if not BACKUP_DIR.exists():
            return
        backups = sorted(BACKUP_DIR.glob(f"{self.display_name}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[MAX_BACKUPS:]:
            old.unlink(missing_ok=True)

    @abstractmethod
    def apply(self, profile_data: dict) -> None:
        """应用配置"""

    @abstractmethod
    def detect(self) -> bool:
        """检测客户端是否安装（配置目录是否存在）"""


class ClaudeCliClient(ClientBase):
    """Claude Code CLI 配置写入（合并式更新，保留用户现有设置）"""

    _path = Path.home() / ".claude" / "settings.json"

    @property
    def config_paths(self) -> list[Path]:
        return [self._path]

    @property
    def display_name(self) -> str:
        return "claude_cli"

    def apply(self, profile_data: dict) -> None:
        api_key = profile_data.get("api_key", "")
        api_url = profile_data.get("api_url", "")
        model = profile_data.get("model", "claude-opus-4-6")

        # 读取现有配置，保留 permissions、allowedTools 等用户设置
        existing = {}
        if self._path.exists():
            try:
                existing = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                existing = {}

        # 只更新 env 和 model 字段
        env = existing.setdefault("env", {})
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        env["ANTHROPIC_BASE_URL"] = api_url
        env["ANTHROPIC_MODEL"] = model
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
        existing["model"] = "opus"

        self._path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(self._path, existing)

    def detect(self) -> bool:
        return self._path.parent.exists()


class VSCodePluginClient(ClientBase):
    """VSCode 插件配置写入（外科式更新）"""

    _path = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json"

    @property
    def config_paths(self) -> list[Path]:
        return [self._path]

    @property
    def display_name(self) -> str:
        return "vscode"

    def apply(self, profile_data: dict) -> None:
        api_url = profile_data.get("api_url", "")
        api_key = profile_data.get("api_key", "")

        # 读取现有配置（容忍 JSONC 格式：解析失败时保留原文件，只更新目标字段）
        existing = {}
        if self._path.exists():
            raw = self._path.read_text(encoding="utf-8")
            try:
                existing = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # VSCode settings.json 可能含注释，无法解析时跳过，不覆盖原文件
                raise RuntimeError(
                    f"VSCode settings.json 格式异常（可能含注释），请手动编辑: {self._path}"
                )

        # 只替换 claudeCode.environmentVariables
        env_vars = [
            {"name": "ANTHROPIC_BASE_URL", "value": api_url},
            {"name": "ANTHROPIC_AUTH_TOKEN", "value": api_key},
        ]
        if profile_data.get("model"):
            env_vars.append({"name": "ANTHROPIC_MODEL", "value": profile_data["model"]})
        existing["claudeCode.environmentVariables"] = env_vars
        self._path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(self._path, existing)

    def detect(self) -> bool:
        return self._path.parent.exists()


class CodexClient(ClientBase):
    """Codex 配置写入（两个文件，合并更新保留用户设置）"""

    _auth_path = Path.home() / ".codex" / "auth.json"
    _config_path = Path.home() / ".codex" / "config.toml"

    @property
    def config_paths(self) -> list[Path]:
        return [self._auth_path, self._config_path]

    @property
    def display_name(self) -> str:
        return "codex"

    def _parse_toml(self) -> dict[str, dict[str, str]]:
        """解析简单 TOML 为 {section: {key: raw_value}}，顶层 section 名为空字符串"""
        sections: dict[str, dict[str, str]] = {"": {}}
        if not self._config_path.exists():
            return sections
        current = ""
        for line in self._config_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("["):
                current = stripped.strip("[]").strip()
                sections.setdefault(current, {})
                continue
            if "=" in stripped:
                key, _, val = stripped.partition("=")
                sections.setdefault(current, {})[key.strip()] = val.strip()
        return sections

    def _write_toml(self, sections: dict[str, dict[str, str]]) -> None:
        """将 sections 写回 TOML"""
        lines = []
        for k, v in sections.get("", {}).items():
            lines.append(f"{k} = {v}")
        for name, data in sections.items():
            if name == "":
                continue
            lines.append("")
            lines.append(f"[{name}]")
            for k, v in data.items():
                lines.append(f"{k} = {v}")
        _atomic_write_text(self._config_path, "\n".join(lines) + "\n")

    def apply(self, profile_data: dict) -> None:
        self._auth_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存旧 auth.json 用于回滚
        old_auth_bytes = None
        if self._auth_path.exists():
            old_auth_bytes = self._auth_path.read_bytes()

        # auth.json
        auth = {"OPENAI_API_KEY": profile_data.get("api_key", "")}
        _atomic_write_json(self._auth_path, auth)

        # config.toml — 读取已有配置，合并更新
        try:
            provider_name = profile_data.get("provider_name", "custom")
            model = profile_data.get("model", "gpt-5.3-codex")
            effort = profile_data.get("reasoning_effort", "high")
            base_url = profile_data.get("base_url", "")

            sections = self._parse_toml()

            # 更新顶层（只改我们管理的字段，保留其余）
            top = sections.setdefault("", {})
            top["model_provider"] = f'"{provider_name}"'
            top["model"] = f'"{model}"'
            top["model_reasoning_effort"] = f'"{effort}"'
            top.setdefault("disable_response_storage", "true")

            # 更新 provider section（保留已有的额外设置）
            sec_name = f"model_providers.{provider_name}"
            sec = sections.setdefault(sec_name, {})
            sec["name"] = f'"{provider_name}"'
            sec["wire_api"] = '"responses"'
            sec["requires_openai_auth"] = "true"
            sec["base_url"] = f'"{base_url}"'

            self._write_toml(sections)
        except Exception:
            # config.toml 写入失败，回滚 auth.json
            if old_auth_bytes is not None:
                _atomic_write_text(self._auth_path, old_auth_bytes.decode("utf-8"))
            elif self._auth_path.exists():
                self._auth_path.unlink()
            raise

    def detect(self) -> bool:
        return self._auth_path.parent.exists()


class GeminiClient(ClientBase):
    """Gemini CLI 配置写入（.env + settings.json）"""

    _env_path = Path.home() / ".gemini" / ".env"
    _settings_path = Path.home() / ".gemini" / "settings.json"

    @property
    def config_paths(self) -> list[Path]:
        return [self._env_path, self._settings_path]

    @property
    def display_name(self) -> str:
        return "gemini"

    def apply(self, profile_data: dict) -> None:
        self._env_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建环境变量
        env_vars: dict[str, str] = {}
        if profile_data.get("api_key"):
            env_vars["GEMINI_API_KEY"] = profile_data["api_key"]
        if profile_data.get("base_url"):
            env_vars["GOOGLE_GEMINI_BASE_URL"] = profile_data["base_url"]
        if profile_data.get("model"):
            env_vars["GEMINI_MODEL"] = profile_data["model"]
        # 支持额外自定义环境变量
        for k, v in profile_data.get("extra_env", {}).items():
            env_vars[k] = v

        # 写入 .env 文件
        lines = [f"{k}={v}" for k, v in sorted(env_vars.items())]
        _atomic_write_text(self._env_path, "\n".join(lines) + "\n")

        # 写入 settings.json — 只更新 security.auth.selectedType，保留其他字段
        existing = {}
        if self._settings_path.exists():
            try:
                existing = json.loads(self._settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                existing = {}

        security = existing.setdefault("security", {})
        auth = security.setdefault("auth", {})
        auth["selectedType"] = "gemini-api-key"

        _atomic_write_json(self._settings_path, existing)

    def detect(self) -> bool:
        return self._env_path.parent.exists()


class OpenCodeClient(ClientBase):
    """OpenCode 配置写入（外科式更新）"""

    _path = Path.home() / ".config" / "opencode" / "opencode.json"

    @property
    def config_paths(self) -> list[Path]:
        return [self._path]

    @property
    def display_name(self) -> str:
        return "opencode"

    def apply(self, profile_data: dict) -> None:
        # 读取现有配置
        existing = {}
        if self._path.exists():
            try:
                existing = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                existing = {}

        if "provider" not in existing:
            existing["provider"] = {}

        provider_id = profile_data.get("provider_id", "anthropic")
        npm_pkg = profile_data.get("npm", "")
        display_name = profile_data.get("display_name", "")
        api_key = profile_data.get("api_key", "")
        base_url = profile_data.get("base_url", "")
        new_models = profile_data.get("models", {})

        # 获取已有的 provider entry，合并而非替换
        entry = existing["provider"].get(provider_id, {})

        # 更新 options
        entry.setdefault("options", {})
        entry["options"]["apiKey"] = api_key
        entry["options"]["baseURL"] = base_url

        # 合并 models（更新已有 + 添加新的，不删除其他）
        entry.setdefault("models", {})
        for model_name, model_config in new_models.items():
            entry["models"][model_name] = model_config

        if display_name:
            entry["name"] = display_name
        if npm_pkg:
            entry["npm"] = npm_pkg

        existing["provider"][provider_id] = entry

        self._path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(self._path, existing)

    def detect(self) -> bool:
        return self._path.parent.exists()


# 客户端实例注册
ALL_CLIENTS = {
    "claude_cli": ClaudeCliClient(),
    "vscode": VSCodePluginClient(),
    "codex": CodexClient(),
    "gemini": GeminiClient(),
    "opencode": OpenCodeClient(),
}
