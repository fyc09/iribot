"""Configuration for the Agent application."""

import json
from pathlib import Path
from threading import Lock
from typing import Any

from dotenv import dotenv_values
from pydantic import BaseModel, Field

_CONFIG_PATH = Path.cwd() / "config.json"
_ENV_PATH = Path.cwd() / ".env"
_settings_lock = Lock()


class Settings(BaseModel):
    """Application settings."""

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4-vision-preview"
    openai_base_url: str | None = None

    # Application Configuration
    debug: bool = False
    app_title: str = "Agent Application"

    # Shell Configuration
    bash_path: str = "bash"
    shell_type: str = "auto"

    # CORS Configuration
    cors_origins: list[str] = Field(default_factory=list)

    # Tool History Configuration
    tool_history_rounds: int = 10
    enable_thinking: bool = False


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_cors_origins(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
    except json.JSONDecodeError:
        pass
    return [v.strip() for v in raw.split(",") if v.strip()]


def _settings_from_env_file() -> Settings:
    env = dotenv_values(_ENV_PATH)
    return Settings(
        openai_api_key=env.get("OPENAI_API_KEY", "") or "",
        openai_model=env.get("OPENAI_MODEL", "gpt-4-vision-preview") or "gpt-4-vision-preview",
        openai_base_url=env.get("OPENAI_BASE_URL") or None,
        debug=_parse_bool(env.get("DEBUG")),
        app_title=env.get("APP_TITLE", "Agent Application") or "Agent Application",
        bash_path=env.get("BASH_PATH", "bash") or "bash",
        shell_type=env.get("SHELL_TYPE", "auto") or "auto",
        cors_origins=_parse_cors_origins(env.get("CORS_ORIGINS")),
        tool_history_rounds=int(env.get("TOOL_HISTORY_ROUNDS", 10) or 10),
        enable_thinking=_parse_bool(env.get("ENABLE_THINKING")),
    )


def _write_settings_to_disk(new_settings: Settings) -> None:
    _CONFIG_PATH.write_text(
        json.dumps(new_settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_settings() -> Settings:
    """Load settings from config.json; migrate from .env if needed."""
    if _CONFIG_PATH.exists():
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return Settings.model_validate(data)

    if _ENV_PATH.exists():
        migrated = _settings_from_env_file()
        _write_settings_to_disk(migrated)
        return migrated

    defaults = Settings()
    _write_settings_to_disk(defaults)
    return defaults


def update_settings(partial: dict[str, Any]) -> Settings:
    """Update in-memory settings and persist to disk."""
    with _settings_lock:
        merged = settings.model_dump()
        merged.update(partial)
        new_settings = Settings.model_validate(merged)
        _write_settings_to_disk(new_settings)
        for key, value in new_settings.model_dump().items():
            setattr(settings, key, value)
        return settings


settings = load_settings()
