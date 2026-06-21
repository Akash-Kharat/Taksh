import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Taksh Backend"
    API_V1_STR: str = "/api/v1"
    
    # Binding exclusively to local loopback interface for safety
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Workspace storage configuration (.taksh/ directory)
    TAKSH_DIR: Path = Path("./.taksh")
    
    # Database Configuration
    DATABASE_NAME: str = "taksh.db"
    
    # ChromaDB Configuration
    CHROMA_DIR: Path = Path("./.taksh/chroma")
    
    # Log Configurations
    LOG_DIR: Path = Path("./.taksh/logs")
    LOG_FILE_NAME: str = "app.log"
    LOG_LEVEL: str = "INFO"
    
    # Source of truth core identity path (relative to backend/)
    IDENTITY_PATH: Path = Path("../docs/Vision/taksh_identity.md")
    
    # Skill Registry configurations
    SKILLS_MANIFEST_DIR: Path = Path("./app/services/skills/manifests")

    # API keys loaded safely from environment
    GEMINI_API_KEY: str = ""
    GEMINI_LIVE_API_URL: str = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidirectionalGenerateContent"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def DATABASE_URL(self) -> str:
        # Guarantee SQLite database path matches under .taksh directory
        self.TAKSH_DIR.mkdir(parents=True, exist_ok=True)
        db_path = self.TAKSH_DIR / self.DATABASE_NAME
        return f"sqlite:///{db_path.resolve().as_posix()}"

settings = Settings()
