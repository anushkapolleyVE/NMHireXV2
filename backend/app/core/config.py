"""Application settings, loaded from environment variables (.env supported)."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Dynamically point to the backend root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # OpenAI (GPT-5.6 model for extraction, evaluation, and OCR)
    OPENAI_API_KEY: str = ""

    # WhatsApp API
    WHATSAPP_API_KEY: str = ""
    WHATSAPP_STAGE_NUMBER: str = ""

    # Model used for structured JSON extraction (JD + resume).
    EXTRACTION_MODEL: str = "gpt-4o"

    # Model used for candidate evaluation (boolean satisfaction flags).
    EVALUATION_MODEL: str = "gpt-4o"

    # --- Search / ranking (3-stage funnel) ---
    TOP_K_VECTOR: int = 150      # fallback semantic search width, used only if stage 1 finds nobody
    SEMANTIC_TOP_K: int = 100    # stage 2 output size -- candidates that reach the AI scorecard
    TOP_N: int = 10              # final shortlist size shown to the recruiter
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # --- File storage ---
    RESUME_DIR: str = "data/resumes"
    JD_DIR: str = "data/job_descriptions"

    class Config:
        env_file = str(ENV_PATH)
        extra = "ignore"

settings = Settings()