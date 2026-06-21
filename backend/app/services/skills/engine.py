from typing import List, Set
from app.core.logger import skills_logger
from app.schemas.telemetry import TelemetryPayload
from app.services.skills.registry import SkillsRegistry

class SkillsEngine:
    """Evaluates active skills and constructs target instruction overlays based on workspace conditions."""
    def __init__(self):
        self.registry = SkillsRegistry()
        self.registry.load_manifests()
        self.active_skill_names: Set[str] = set()
        skills_logger.info("SkillsEngine initialized and manifests registry loaded.")

    def evaluate_active_skills(self, telemetry: TelemetryPayload) -> List[str]:
        """Matches file name extensions and error messages against loaded manifests' trigger rules."""
        self.active_skill_names.clear()
        
        for skill in self.registry.get_all_skills():
            rules = skill.activation_rules
            for pattern in rules.file_patterns:
                clean_pattern = pattern.replace("*", "")
                if clean_pattern and clean_pattern in telemetry.active_file:
                    self.active_skill_names.add(skill.name)
                    break
            
            if telemetry.compiler_error:
                for kw in rules.keywords:
                    if kw.lower() in telemetry.compiler_error.lower():
                        self.active_skill_names.add(skill.name)
                        break

        return list(self.active_skill_names)

    def get_active_overlays(self) -> str:
        """Assembles prompt overlay constraints from all currently active skills."""
        overlays = []
        for name in self.active_skill_names:
            skill = self.registry.skills.get(name)
            if skill:
                overlay = skill.prompt_overlay
                constraints = "\n".join([f"- {c}" for c in overlay.technical_constraints])
                section = (
                    f"### Skill: {skill.name}\n"
                    f"Role Override: {overlay.role}\n"
                    f"Pedagogical Instruction: {overlay.pedagogical_instructions}\n"
                    f"Technical Constraints:\n{constraints}\n"
                )
                overlays.append(section)
        
        return "\n".join(overlays) if overlays else "No active skills overlay prompts active."
