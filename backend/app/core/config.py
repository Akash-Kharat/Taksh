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
    
    # Knowledge / RAG configurations
    DOCS_DIR: Path = Path("../docs")
    KNOWLEDGE_CHUNK_SIZE: int = 500
    KNOWLEDGE_CHUNK_OVERLAP: int = 50
    MOCK_EMBEDDINGS: bool = False
    
    # Cognitive / Orchestration configurations
    MAX_KNOWLEDGE_CHUNKS: int = 5
    MAX_RECENT_EVENTS: int = 10
    PROMPT_VERSION: str = "v1"
    
    # LLM Gateway configurations
    DEFAULT_LLM_PROVIDER: str = "mock"
    DEFAULT_LLM_MODEL: str = "gemini-1.5-flash"
    DEFAULT_MAX_TOKENS: int = 1024
    DEFAULT_TEMPERATURE: float = 0.2
    
    # Skill Registry configurations
    SKILLS_MANIFEST_DIR: Path = Path("./app/services/skills/manifests")

    # Workspace Intelligence configurations
    WORKSPACE_DIR: Path = Path("..")
    MAX_SELECTION_CONTENT_CHARS: int = 5000
    MIN_SNAPSHOT_INTERVAL_SECONDS: int = 5
    MAX_SCAN_FILES: int = 10000
    MAX_SCAN_DEPTH: int = 20
    ERROR_RETENTION_DAYS: int = 30
    MAX_WORKSPACE_ERRORS: int = 5
    MAX_RECENT_COMMITS: int = 5
    MAX_FRAMEWORKS: int = 10

    # Tool & Action Framework configurations
    MAX_TOOL_OUTPUT_CHARS: int = 10000
    APPROVAL_EXPIRATION_HOURS: int = 24

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
