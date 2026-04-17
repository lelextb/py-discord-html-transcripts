"""
Configuration loader with validation and environment variable handling.
Loads from .env file with defaults and type conversion.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env from the same directory as this file
CONFIG_DIR = Path(__file__).parent.absolute()
ENV_PATH = CONFIG_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class BotConfig:
    """Immutable configuration container."""

    def __init__(self) -> None:
        self.discord_token: str = self._require_str("DISCORD_TOKEN")
        self.server_id: int = self._require_int("SERVER_ID")
        self.transcript_dir: Path = self._get_transcript_dir()
        self.max_messages: int = self._get_max_messages()
        self.slowdown_threshold: int = 45      # messages before enabling delays
        self.burst_size: int = 30              # messages per batch before sleep
        self.sleep_duration: float = 1.0       # seconds per burst
        self.quest_badge_path: str = os.getenv("QUEST_BADGE_PATH", "")   # fixed: now inside __init__

    @staticmethod
    def _require_str(key: str) -> str:
        value = os.getenv(key)
        if not value or not value.strip():
            raise ConfigError(f"Missing required environment variable: {key}")
        return value.strip()

    @staticmethod
    def _require_int(key: str) -> int:
        value = os.getenv(key)
        if not value or not value.strip():
            raise ConfigError(f"Missing required environment variable: {key}")
        try:
            return int(value)
        except ValueError:
            raise ConfigError(f"Invalid integer for {key}: {value}")

    def _get_transcript_dir(self) -> Path:
        dir_name = os.getenv("TRANSCRIPT_DIR", "transcripts")
        path = CONFIG_DIR / dir_name
        path.mkdir(exist_ok=True, parents=True)
        return path

    def _get_max_messages(self) -> int:
        raw = os.getenv("MAX_MESSAGES", "0")
        try:
            val = int(raw)
            return val if val > 0 else 0   # 0 means unlimited
        except ValueError:
            return 0


# Singleton instance for global import
config = BotConfig()