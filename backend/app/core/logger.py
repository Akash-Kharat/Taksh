import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from app.core.config import settings

class CategoryLoggerAdapter(logging.LoggerAdapter):
    """Adapter to inject log categories into formatter dynamically."""
    def process(self, msg, kwargs):
        category = self.extra.get("category", "SYSTEM") if self.extra else "SYSTEM"
        kwargs["extra"] = {"category": category}
        return f"[Category: {category}] {msg}", kwargs

def setup_logging() -> None:
    """Configures centralized logging streams and file rotation targets."""
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file_path = settings.LOG_DIR / settings.LOG_FILE_NAME

    log_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Clear existing handlers
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 1. Console Handler (stdout/development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

def get_category_logger(category: str) -> logging.LoggerAdapter:
    """Returns an adapter logger wrapping messages under custom categories."""
    logger = logging.getLogger("taksh")
    return CategoryLoggerAdapter(logger, {"category": category})

# Predefined adapters for system categories
api_logger = get_category_logger("API")
ws_logger = get_category_logger("WebSocket")
voice_logger = get_category_logger("Voice")
memory_logger = get_category_logger("Memory")
skills_logger = get_category_logger("Skills")
knowledge_logger = get_category_logger("Knowledge")
db_logger = get_category_logger("Database")
system_logger = get_category_logger("SYSTEM")
workspace_logger = get_category_logger("Workspace")
tool_logger = get_category_logger("Tools")
