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
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "noreply@estimator.local")
    smtp_tls: bool = os.getenv("SMTP_TLS", "true").lower() == "true"

    class Config:
        env_file = ".env"


settings = Settings()
