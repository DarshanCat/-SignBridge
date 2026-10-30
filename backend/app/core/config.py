from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables / .env (no secrets)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="SIGNBRIDGE_", extra="ignore", protected_namespaces=("settings_",)
    )

    app_name: str = "SignBridge API"
    version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    model_dir: Path = BACKEND_DIR / "models"
    sign_registry: Path = BACKEND_DIR / "config" / "sign_registry.json"
    min_confidence: float = 0.5
    max_body_bytes: int = 2_000_000  # reject larger request bodies (300 frames of landmarks is about 0.75 MB)
    translation_config: Path = BACKEND_DIR / "config" / "translation.json"
    gloss_dictionary: Path = BACKEND_DIR / "config" / "gloss_dictionary.json"
    spacy_model: str = "en_core_web_sm"
    record_dir: Path = BACKEND_DIR.parent / "data" / "recorded"  # self-recorded landmark takes (no video), git-ignored
    animation_dir: Path = BACKEND_DIR.parent / "frontend" / "public" / "animations"


@lru_cache
def get_settings() -> Settings:
    return Settings()
