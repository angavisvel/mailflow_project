"""
Central place to load configuration from environment variables.
Nothing here should ever be hard-coded with real secrets -
values are pulled from a local .env file (see .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8080/callback"
    )

    # Minimum scopes needed for Module 1 (login + future read access).
    GOOGLE_SCOPES: list[str] = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    # JWT Session Tokens (providing both naming styles for compatibility)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-.env")
    SECRET_KEY: str = os.getenv("JWT_SECRET", "change-me-in-.env")
    
    JWT_ALGORITHM: str = "HS256"
    ALGORITHM: str = "HS256"
    
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    FRONTEND_DEEP_LINK: str = os.getenv("FRONTEND_DEEP_LINK", "emailtodo://oauth-callback")

    # Module 3: Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()