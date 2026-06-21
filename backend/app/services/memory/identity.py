import os
import threading
from pathlib import Path
from app.core.config import settings
from app.core.logger import memory_logger

class CoreIdentityManager:
    """Immutable Core Identity Layer.
    
    Thread-safe Singleton that reads and caches `.taksh/identity/core_identity.md` in memory at startup.
    Blocks any override attempts.
    """
    _instance = None
    _lock = threading.Lock()
    _identity_content: str = ""

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(CoreIdentityManager, cls).__new__(cls)
        return cls._instance

    def initialize(self) -> None:
        """Loads core identity markdown at startup."""
        identity_path = settings.IDENTITY_DIR / settings.IDENTITY_FILE_NAME
        memory_logger.info(f"Loading Core Identity from: {identity_path}")
        
        if not identity_path.exists():
            settings.IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
            default_content = (
                "# Core Identity — Taksh\n"
                "You are Taksh, an expert Socratic engineering companion.\n"
                "Pedagogical directive: Always guide developers to first principles.\n"
            )
            try:
                with open(identity_path, "w", encoding="utf-8") as f:
                    f.write(default_content)
                memory_logger.info(f"Generated default core identity markdown at: {identity_path}")
            except Exception as ex:
                memory_logger.error(f"Failed writing core identity: {ex}")
                self._identity_content = default_content
                return
        
        try:
            with open(identity_path, "r", encoding="utf-8") as f:
                self._identity_content = f.read()
            memory_logger.info("Core Identity successfully loaded and cached in memory.")
        except Exception as ex:
            memory_logger.error(f"Failed reading core identity file: {ex}")
            self._identity_content = "You are Taksh, a Socratic engineering companion."

    def get_identity(self) -> str:
        """Returns the cached, immutable core identity markdown string."""
        return self._identity_content
