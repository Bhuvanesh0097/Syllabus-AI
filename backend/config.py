"""
Configuration management for Syllabus AI Study Assistant.
Loads environment variables and provides typed settings across the application.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────
    app_name: str = "Syllabus AI Study Assistant"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS"
    )

    # ── LLM API Keys ─────────────────────────────────────────────
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # ── Supabase ─────────────────────────────────────────────────
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")

    # ── ChromaDB ─────────────────────────────────────────────────
    chroma_persist_dir: str = Field(
        default="./chroma_db", alias="CHROMA_PERSIST_DIR"
    )

    # ── Document Storage ─────────────────────────────────────────
    document_storage_dir: str = Field(
        default="./documents", alias="DOCUMENT_STORAGE_DIR"
    )

    # ── LLM Settings ─────────────────────────────────────────────
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")  # "groq" or "gemini"
    llm_model: str = Field(default="llama-3.3-70b-versatile", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=8192, alias="LLM_MAX_TOKENS")

    # ── Admin ────────────────────────────────────────────────
    admin_pin: str = Field(default="1234", alias="ADMIN_PIN")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# ── Singleton instance ───────────────────────────────────────────
settings = Settings()
