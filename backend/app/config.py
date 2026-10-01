# """Application settings, loaded from environment variables (.env supported)."""
# from pydantic_settings import BaseSettings
 
 
# class Settings(BaseSettings):
#     # --- Database ---
#     DATABASE_URL: str
 
#     # --- Groq (LLM extraction + evaluation) ---
#     # Get a free key at https://console.groq.com/keys
#     GROQ_API_KEY: str
#     GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
 
#     # Groq model used for structured JSON extraction (JD + resume).
#     # openai/gpt-oss-120b = higher quality, slower/costlier.
#     # openai/gpt-oss-20b  = faster/cheaper, use if 120b hits rate limits often.
#     EXTRACTION_MODEL: str = "openai/gpt-oss-120b"
 
#     # Groq model used for candidate evaluation (boolean satisfaction flags).
#     EVALUATION_MODEL: str = "openai/gpt-oss-120b"
 
#     # --- Search / ranking (3-stage funnel) ---
#     TOP_K_VECTOR: int = 150      # fallback semantic search width, used only if stage 1 finds nobody
#     SEMANTIC_TOP_K: int = 100    # stage 2 output size -- candidates that reach the AI scorecard
#     TOP_N: int = 10              # final shortlist size shown to the recruiter
 
#     # --- File storage ---
#     RESUME_DIR: str = "data/resumes"
#     JD_DIR: str = "data/job_descriptions"
 
#     class Config:
#         env_file = ".env"
#         extra = "ignore"
 
 
# settings = Settings()
"""Application settings, loaded from environment variables (.env supported)."""
from pydantic_settings import BaseSettings


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
        env_file = ".env"
        extra = "ignore"


settings = Settings()
