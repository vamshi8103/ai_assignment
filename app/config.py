"""
Configuration module for the Conversation Evaluation Benchmark System.
Uses environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # ── LLM Configuration ──
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "mistralai/Mixtral-8x7B-Instruct-v0.1")
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "huggingface")
    MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", "2048"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))

    # ── Scoring Configuration ──
    FACET_BATCH_SIZE: int = int(os.getenv("FACET_BATCH_SIZE", "15"))
    SCORE_MIN: int = 1
    SCORE_MAX: int = 5
    CONFIDENCE_MIN: float = 0.0
    CONFIDENCE_MAX: float = 1.0

    # ── Data Paths ──
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FACETS_CSV: str = os.path.join(BASE_DIR, "data", "facets_cleaned.csv")

    # ── Server Configuration ──
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── Rate Limiting ──
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "2.0"))
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "120.0"))


settings = Settings()
