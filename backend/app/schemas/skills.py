from typing import List
from pydantic import BaseModel

class ActivationRules(BaseModel):
    file_patterns: List[str]
    keywords: List[str]

class PromptOverlay(BaseModel):
    role: str
    pedagogical_instructions: str
    technical_constraints: List[str]

class SkillManifest(BaseModel):
    name: str
    description: str
    activation_rules: ActivationRules
    prompt_overlay: PromptOverlay
