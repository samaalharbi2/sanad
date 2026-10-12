"""قراءة إعدادات المشروع من config/settings.yaml."""
from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def load_settings() -> dict:
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    # متغير البيئة يتقدم على الملف
    settings["ollama"]["host"] = os.getenv("OLLAMA_HOST", settings["ollama"]["host"])
    return settings


def path(key: str) -> Path:
    """يرجع مسارًا مطلقًا من قسم paths في الإعدادات."""
    return ROOT / load_settings()["paths"][key]
