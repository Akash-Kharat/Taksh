import hashlib
import threading
from pathlib import Path
from app.core.config import settings
from app.core.logger import memory_logger

class CoreIdentityManager:
    """Immutable Core Identity Layer.
    
    Thread-safe Singleton that reads, hashes, and caches docs/Vision/taksh_identity.md in memory.
    """
    _instance = None
    _lock = threading.Lock()
    _identity_content: str = ""
    _identity_hash: str = ""
    _initialized: bool = False
    _fallback_active: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(CoreIdentityManager, cls).__new__(cls)
        return cls._instance

    def initialize(self) -> None:
        """Loads and hashes core identity markdown at startup."""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            identity_path = settings.IDENTITY_PATH
            
            if not identity_path.exists():
                # Critical logging block
                memory_logger.critical("Core Identity file missing.")
                memory_logger.critical(f"Configured Path: {identity_path}")
                memory_logger.critical("Fallback Identity Activated.")
                
                self._identity_content = (
                    "# Core Identity — Taksh\n"
                    "You are Taksh, an expert Socratic engineering companion.\n"
                    "Pedagogical directive: Always guide developers to first principles.\n"
                )
                self._fallback_active = True
            else:
                try:
                    with open(identity_path, "r", encoding="utf-8") as f:
                        self._identity_content = f.read()
                    self._fallback_active = False
                    memory_logger.info("Core Identity successfully loaded and cached in memory.")
                except Exception as ex:
                    memory_logger.error(f"Failed reading core identity file: {ex}")
                    self._identity_content = "You are Taksh, a Socratic engineering companion."
                    self._fallback_active = True
            
            # Generate SHA-256 hash
            hasher = hashlib.sha256()
            hasher.update(self._identity_content.encode("utf-8"))
            self._identity_hash = hasher.hexdigest()
            
            self._initialized = True

    def get_identity(self) -> str:
        return self._identity_content

    def get_metadata(self) -> dict:
        return {
            "loaded": self._initialized and not self._fallback_active,
            "source": str(settings.IDENTITY_PATH.as_posix()),
            "cache_initialized": self._initialized,
            "identity_hash": self._identity_hash
        }
