import os
import threading
import yaml
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.logger import skills_logger
from app.schemas.skills import SkillManifest

class SkillsRegistry:
    """Discovers, parses, and caches externalized YAML skill manifests. Thread-safe Singleton."""
    _instance = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SkillsRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_registry_initialized"):
            return
        self.skills: Dict[str, SkillManifest] = {}
        self._registry_initialized = True

    def load_manifests(self) -> None:
        """Reads all YAML definitions and registers them."""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            manifest_dir = settings.SKILLS_MANIFEST_DIR
            skills_logger.info(f"Scanning for skill manifests in: {manifest_dir}")
            
            if not manifest_dir.exists():
                skills_logger.warning(f"Manifests directory {manifest_dir} does not exist. Creating path.")
                manifest_dir.mkdir(parents=True, exist_ok=True)
            else:
                for filename in os.listdir(manifest_dir):
                    if filename.endswith(".yaml") or filename.endswith(".yml"):
                        file_path = manifest_dir / filename
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = yaml.safe_load(f)
                            manifest = SkillManifest.model_validate(data)
                            self.skills[manifest.name] = manifest
                            skills_logger.info(f"Loaded skill manifest: '{manifest.name}' from {filename}")
                        except Exception as ex:
                            skills_logger.error(f"Failed parsing skill manifest {filename}: {ex}")
            
            # Post-load verification rules
            skill_count = len(self.skills)
            skills_logger.info(f"Loaded {skill_count} skill manifests successfully.")
            
            if skill_count == 0:
                skills_logger.error("Registry must contain at least one valid skill. Zero valid skills loaded!")
                
            self._initialized = True

    def get_all_skills(self) -> List[SkillManifest]:
        return list(self.skills.values())

    def get_skill(self, name: str) -> Optional[SkillManifest]:
        """Lookup skill case-insensitively, handling hyphens and spaces."""
        query = name.replace("-", " ").lower()
        for skill_name, manifest in self.skills.items():
            if skill_name.lower() == query:
                return manifest
        return None

    def get_diagnostics(self) -> dict:
        return {
            "loaded_skills": len(self.skills),
            "manifest_directory": str(settings.SKILLS_MANIFEST_DIR.as_posix()),
            "registry_initialized": self._initialized
        }
