from typing import List
from fastapi import APIRouter, HTTPException
from app.schemas.skills import SkillManifest
from app.services.skills.registry import SkillsRegistry

router = APIRouter(prefix="/skills")

@router.get("/info")
def get_skills_info():
    registry = SkillsRegistry()
    return registry.get_diagnostics()

@router.get("/", response_model=List[SkillManifest])
def list_skills():
    registry = SkillsRegistry()
    return registry.get_all_skills()

@router.get("/{skill_name}", response_model=SkillManifest)
def get_skill(skill_name: str):
    registry = SkillsRegistry()
    skill = registry.get_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill
