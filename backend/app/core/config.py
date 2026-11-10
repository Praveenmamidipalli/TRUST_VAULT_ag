import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TrustVault"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security: SECRET_KEY is strictly required and must be at least 64 hex characters (32 bytes)
    SECRET_KEY: str = Field(min_length=64)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./trustvault.db"
    
    # Private Storage
    STORAGE_DIR: str = os.environ.get(
        "STORAGE_DIR",
        os.path.abspath(os.path.join(os.getcwd(), "storage", "private"))
    )
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("SECRET_KEY")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        insecure_patterns = (
            "change_me", "replace_me", "your_", "default", "secret",
            "trustvault-production-secret", "generate-with-openssl"
        )
        val_clean = value.strip().lower()
        if not val_clean:
            raise ValueError("SECRET_KEY cannot be empty.")
        if any(val_clean.startswith(p) or p in val_clean for p in insecure_patterns):
            raise ValueError(
                "Insecure or placeholder SECRET_KEY detected! Production requires a cryptographically "
                "strong secret. Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        if len(value.strip()) < 64:
            raise ValueError("SECRET_KEY must be at least 64 characters (e.g. 32 random bytes hex-encoded).")
        return value
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

# Ensure private storage directory exists gracefully
try:
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
except Exception as e:
    print(f"[!] Storage directory initialization warning: {e}")

