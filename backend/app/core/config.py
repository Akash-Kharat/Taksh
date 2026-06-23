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

    # Controlled Execution Layer (MS-11) configurations
    DEFAULT_EXECUTION_TIMEOUT: int = 60
    MAX_STDOUT_CHARS: int = 10000
    MAX_STDERR_CHARS: int = 5000
    MAX_CONCURRENT_EXECUTIONS: int = 2
    ALLOWED_GIT_COMMANDS: list[str] = ["diff", "log", "status"]
    MAX_PYTEST_ARGUMENTS: int = 5
    MAX_TEST_PATH_DEPTH: int = 5

    # Conversation Intelligence Layer (MS-12) configurations
    MAX_PROJECT_SNAPSHOTS: int = 3
    MAX_PREFERENCES: int = 10

    # Voice Transport Layer (MS-13) configurations
    VOICE_SAMPLE_RATE: int = 16000
    VOICE_CHANNELS: int = 1
    VOICE_BUFFER_SIZE_FRAMES: int = 256
    MAX_AUDIO_FRAME_BYTES: int = 65536
    MAX_VOICE_SESSIONS: int = 10
    VOICE_IDLE_TIMEOUT_SECONDS: int = 30


    # Provider Integration Layer (MS-15/16) configurations
    DEFAULT_STT_PROVIDER: str = "mock"
    DEFAULT_TTS_PROVIDER: str = "mock"
    DEFAULT_REALTIME_PROVIDER: str = "gemini_live"
    ENABLE_PROVIDER_HEALTH_CHECKS: bool = True
    PROVIDER_REQUEST_TIMEOUT_SECONDS: int = 30
    PROVIDER_HEALTH_RETENTION_DAYS: int = 30
    MAX_PROVIDER_QUEUE_SIZE: int = 100

    # Live Provider Integration (MS-16) configurations
    GEMINI_LIVE_MODEL: str = "gemini-2.5-flash-preview-native-audio-dialog"
    GEMINI_LIVE_TIMEOUT_SECONDS: int = 60
    MAX_PROVIDER_RECONNECT_ATTEMPTS: int = 3
    PROVIDER_RECONNECT_DELAY_SECONDS: int = 2
    ENABLE_PROVIDER_FALLBACK: bool = True
    PROVIDER_FAILURE_THRESHOLD: int = 5
    MAX_PROVIDER_RESPONSE_CHARS: int = 10000
    MAX_PROVIDER_RESPONSE_SEGMENTS: int = 50

    # API keys loaded safely from environment
    GEMINI_API_KEY: str = ""
    GEMINI_LIVE_API_URL: str = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidirectionalGenerateContent"

    # End-to-End Voice Conversation (MS-17) configurations
    MAX_CONVERSATION_TURNS: int = 10
    MAX_RESPONSE_SEGMENTS: int = 50
    MAX_RESPONSE_CHARS: int = 10000
    MAX_PLAYBACK_QUEUE_ITEMS: int = 100
    MEMORY_RETRIEVAL_LIMIT: int = 5

    # Product Hardening (MS-19) configurations
    MAX_PROMPT_CHARS: int = 25000
    MAX_MEMORY_ITEMS: int = 10
    MAX_EPISODES: int = 5
    HEALTH_CHECK_TIMEOUT_SECONDS: int = 5
    HEALTH_HISTORY_RETENTION_DAYS: int = 30

    # Release Candidate (MS-20) configurations
    TAKSH_PROFILE: str = "development"  # development | lab | production


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
