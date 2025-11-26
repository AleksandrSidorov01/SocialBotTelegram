"""Configuration settings for the Tamagochi bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root directory
BASE_DIR = Path(__file__).parent


class Config:
    """Bot configuration class."""

    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Database (SQLite - local file)
    DB_FILE = os.getenv("DB_FILE", "tamagochi.db")
    DB_PATH = BASE_DIR / DB_FILE

    @property
    def database_url(self) -> str:
        """Get SQLite connection URL."""
        return f"sqlite+aiosqlite:///{self.DB_PATH}"

    # Bot Settings
    TICK_INTERVAL_MINUTES = int(os.getenv("TICK_INTERVAL_MINUTES", "60"))
    CRITICAL_HEALTH_THRESHOLD = int(os.getenv("CRITICAL_HEALTH_THRESHOLD", "10"))
    NIGHT_START_HOUR = int(os.getenv("NIGHT_START_HOUR", "0"))
    NIGHT_END_HOUR = int(os.getenv("NIGHT_END_HOUR", "7"))

    # XP and Evolution
    XP_PER_MESSAGE = int(os.getenv("XP_PER_MESSAGE", "1"))
    XP_PER_FEED = int(os.getenv("XP_PER_FEED", "5"))
    XP_PER_GAME = int(os.getenv("XP_PER_GAME", "10"))

    # Pet Stats (starting values)
    MAX_STAT_VALUE = 100
    STAT_DECAY_PER_TICK = 5  # How much each stat decreases per tick

    # Bad words filter (basic list - can be expanded)
    BAD_WORDS = [
        "бля", "сука", "пизд", "ебан", "хуй", "хер",
        "fuck", "shit", "damn", "ass"
    ]


config = Config()
