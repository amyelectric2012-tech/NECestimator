import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Electrical Estimator"
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-please")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/estimator"
    )
    pdf_dir: str = os.getenv("PDF_DIR", "/tmp/estimator_pdfs")

    class Config:
        env_file = ".env"


settings = Settings()
