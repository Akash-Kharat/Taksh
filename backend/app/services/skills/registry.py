import os
import yaml
from typing import Dict, List
from app.core.config import settings
from app.core.logger import skills_logger
from app.schemas.skills import SkillManifest

class SkillsRegistry:
    """Discovers and parses externalized YAML skill manifests from manifests directory."""
    def __init__(self):
        self.skills: Dict[str, SkillManifest] = {}
        skills_logger.info("SkillsRegistry initialized.")

    def load_manifests(self) -> None:
        """Reads all YAML definitions from manifests directory and registers them."""
        manifest_dir = settings.SKILLS_MANIFEST_DIR
        skills_logger.info(f"Scanning for skill manifests in: {manifest_dir}")
        
        if not manifest_dir.exists():
            skills_logger.warning(f"Manifests directory {manifest_dir} does not exist. Creating default path.")
            manifest_dir.mkdir(parents=True, exist_ok=True)
            return

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

    def get_all_skills(self) -> List[SkillManifest]:
        """Returns all registered skill manifests."""
        return list(self.skills.values())
