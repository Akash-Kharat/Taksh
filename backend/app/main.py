from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.core.config import settings
from app.core.logger import setup_logging, system_logger
from app.core.security import enforce_local_loopback
from app.services.memory.identity import CoreIdentityManager
from app.api.endpoints import health, settings as settings_api, knowledge, memory, session, project, goal, learning, identity, skills
from app.api.websockets import voice

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    system_logger.info("Initializing Taksh Backend...")

    # Local SQLite DB setup
    system_logger.info("Running database initializations...")

    # Core Identity Manager
    identity_manager = CoreIdentityManager()
    identity_manager.initialize()
    system_logger.info("✓ Identity Loaded")
    system_logger.info(f"✓ Identity Hash Generated: {identity_manager.get_metadata()['identity_hash']}")

    # Skills Registry
    from app.services.skills.registry import SkillsRegistry
    skills_registry = SkillsRegistry()
    skills_registry.load_manifests()
    system_logger.info("✓ Skill Registry Loaded")
    system_logger.info(f"✓ Total Skills Registered: {len(skills_registry.skills)}")

    system_logger.info("Taksh Backend initialization completed. Ready to serve.")
    yield
    system_logger.info("Shutting down Taksh Backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    dependencies=[Depends(enforce_local_loopback)]
)

# Mount REST API Endpoint Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(settings_api.router, prefix=settings.API_V1_STR)
app.include_router(knowledge.router, prefix=settings.API_V1_STR)
app.include_router(memory.router, prefix=settings.API_V1_STR, tags=["Memory"])
app.include_router(session.router, prefix=settings.API_V1_STR, tags=["Sessions"])
app.include_router(project.router, prefix=settings.API_V1_STR, tags=["Projects"])
app.include_router(goal.router, prefix=settings.API_V1_STR, tags=["Goals"])
app.include_router(learning.router, prefix=settings.API_V1_STR, tags=["Learning History"])
app.include_router(identity.router, prefix=settings.API_V1_STR, tags=["Identity"])
app.include_router(skills.router, prefix=settings.API_V1_STR, tags=["Skills"])

# Mount WebSocket Router
app.include_router(voice.router, prefix=settings.API_V1_STR)
