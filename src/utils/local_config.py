"""
Persistent configuration for local model mode.
Stored in ~/.truth-machine/config.json so it survives across sessions.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field

CONFIG_DIR = Path.home() / ".truth-machine"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class LocalModeConfig:
    enabled: bool = False
    model_tag: str = ""
    ollama_base_url: str = "http://localhost:11434"
    setup_completed: bool = False
    # Snapshot of hardware at setup time (informational)
    hardware_summary: str = ""

    def to_dict(self):
        return asdict(self)


def load_config() -> LocalModeConfig:
    """Load config from disk, returning defaults if missing."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return LocalModeConfig(**{
                k: v for k, v in data.items()
                if k in LocalModeConfig.__dataclass_fields__
            })
        except Exception:
            pass
    return LocalModeConfig()


def save_config(cfg: LocalModeConfig) -> None:
    """Persist config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg.to_dict(), indent=2))


def reset_config() -> None:
    """Delete persisted config."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def is_local_mode() -> bool:
    """Quick check: is the system configured for local inference?"""
    cfg = load_config()
    return cfg.enabled and cfg.setup_completed
