"""Configuration for the Agent Application"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4-vision-preview"
    openai_base_url: Optional[str] = None
    
    # Application Configuration
    debug: bool = False
    app_title: str = "Agent Application"
    
    # Shell Configuration
    bash_path: str = "bash"  # Path to bash executable, defaults to "bash" in PATH
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]


settings = Settings()
