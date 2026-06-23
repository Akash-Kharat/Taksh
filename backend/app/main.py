from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Depends
from app.core.config import settings
from app.core.logger import setup_logging, system_logger
from app.core.security import enforce_local_loopback
from app.core.startup_validator import StartupValidator
from app.core.maintenance import maintenance_scheduler
from app.services.memory.identity import CoreIdentityManager
from app.api.endpoints import (
    health, settings as settings_api, knowledge, memory, session,
    project, goal, learning, identity, skills, orchestrator, chat,
    llm, workspace, tools, conversation,
    voice as voice_endpoints, runtime, providers,
    metrics as metrics_api, system as system_api,
)
from app.api.websockets import voice, connection, voice_transport


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    system_logger.info("Initializing Taksh Backend...")

    # --- Structured Startup Validation (MS-19) ---
    system_logger.info("Running startup validation...")
    validator = StartupValidator()
    validator.validate_all()  # raises RuntimeError on critical failure
    system_logger.info("✓ All critical startup checks passed")

    # --- Core Identity Manager ---
    identity_manager = CoreIdentityManager()
    identity_manager.initialize()
    system_logger.info("✓ Identity Loaded")
    system_logger.info(f"✓ Identity Hash Generated: {identity_manager.get_metadata()['identity_hash']}")

    # --- Skills Registry ---
    from app.services.skills.registry import SkillsRegistry
    skills_registry = SkillsRegistry()
    skills_registry.load_manifests()
    system_logger.info("✓ Skill Registry Loaded")
    system_logger.info(f"✓ Total Skills Registered: {len(skills_registry.skills)}")

    # --- Hydrate in-memory metrics from last DB snapshot (MS-19) ---
    try:
        from app.core.database import SessionLocal
        from app.core.metrics import metrics
        from app.models.database_models import MetricsSnapshot
        from sqlalchemy import desc
        db = SessionLocal()
        try:
            last = db.query(MetricsSnapshot).order_by(desc(MetricsSnapshot.captured_at)).first()
            if last:
                metrics.hydrate({
                    "conversation_count":   last.conversation_count,
                    "turn_count":           last.turn_count,
                    "provider_requests":    last.provider_requests,
                    "provider_failures":    last.provider_failures,
                    "tool_executions":      last.tool_executions,
                    "memory_recalls":       last.memory_recalls,
                    "knowledge_searches":   last.knowledge_searches,
                    "average_latency_ms":   last.average_latency_ms,
                })
                system_logger.info(f"✓ Metrics hydrated from DB snapshot ({last.captured_at})")
            else:
                system_logger.info("✓ Metrics initialised fresh (no prior snapshot)")
        finally:
            db.close()
    except Exception as e:
        system_logger.warning(f"Metrics hydration skipped: {e}")

    # --- Background Tasks ---
    health_task = None
    if settings.ENABLE_PROVIDER_HEALTH_CHECKS:
        from app.services.providers.health import start_health_monitor_loop
        health_task = asyncio.create_task(start_health_monitor_loop())
        system_logger.info("✓ Started Provider Health Monitor Background Task")

    maintenance_task = asyncio.create_task(maintenance_scheduler.start_maintenance_loop())
    system_logger.info("✓ Started Background Maintenance Scheduler")

    system_logger.info("Taksh Backend initialization completed. Ready to serve.")
    yield

    # --- Shutdown ---
    if health_task:
        system_logger.info("Stopping Provider Health Monitor Background Task...")
        health_task.cancel()
        try:
            await health_task
        except Exception:
            pass

    system_logger.info("Stopping Maintenance Scheduler...")
    maintenance_task.cancel()
    try:
        await maintenance_task
    except Exception:
        pass

    # Clean up WebSocket registries, providers, and vector store connections
    system_logger.info("Clearing active WebSocket connections...")
    try:
        from app.services.websocket.manager import ws_manager
        await ws_manager.clear()
    except Exception as e:
        system_logger.warning(f"Error clearing WebSockets: {e}")

    system_logger.info("Disconnecting all active providers...")
    try:
        from app.services.providers.factory import provider_factory
        await provider_factory.disconnect_all()
    except Exception as e:
        system_logger.warning(f"Error disconnecting providers: {e}")

    system_logger.info("Closing ChromaDB vector store clients...")
    try:
        from app.services.knowledge.vector_store import close_all_clients
        close_all_clients()
    except Exception as e:
        system_logger.warning(f"Error closing Chroma clients: {e}")

    system_logger.info("Clearing active runtime and voice sessions...")
    try:
        from app.services.runtime.state_machine import active_state_machines
        from app.services.runtime.output_queue import active_output_queues
        from app.services.voice.session_manager import voice_session_manager
        active_state_machines.clear()
        active_output_queues.clear()
        voice_session_manager.active_sessions.clear()
    except Exception as e:
        system_logger.warning(f"Error clearing runtime/voice sessions: {e}")

    system_logger.info("Shutting down Taksh Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    dependencies=[Depends(enforce_local_loopback)]
)

# Mount REST API Endpoint Routers
app.include_router(health.router,        prefix=settings.API_V1_STR)
app.include_router(settings_api.router,  prefix=settings.API_V1_STR)
app.include_router(knowledge.router,     prefix=settings.API_V1_STR)
app.include_router(memory.router,        prefix=settings.API_V1_STR, tags=["Memory"])
app.include_router(session.router,       prefix=settings.API_V1_STR, tags=["Sessions"])
app.include_router(project.router,       prefix=settings.API_V1_STR, tags=["Projects"])
app.include_router(goal.router,          prefix=settings.API_V1_STR, tags=["Goals"])
app.include_router(learning.router,      prefix=settings.API_V1_STR, tags=["Learning History"])
app.include_router(identity.router,      prefix=settings.API_V1_STR, tags=["Identity"])
app.include_router(skills.router,        prefix=settings.API_V1_STR, tags=["Skills"])
app.include_router(orchestrator.router,  prefix=settings.API_V1_STR, tags=["Orchestrator"])
app.include_router(chat.router,          prefix=settings.API_V1_STR, tags=["Chat"])
app.include_router(llm.router,           prefix=settings.API_V1_STR, tags=["LLM"])
app.include_router(workspace.router,     prefix=settings.API_V1_STR, tags=["Workspace"])
app.include_router(tools.router,         prefix=settings.API_V1_STR, tags=["Tools"])
app.include_router(conversation.router,  prefix=settings.API_V1_STR)
app.include_router(runtime.router,       prefix=settings.API_V1_STR, tags=["Conversation Runtime"])
app.include_router(providers.router,     prefix=settings.API_V1_STR, tags=["Provider Diagnostics"])

# MS-19 new endpoints
app.include_router(metrics_api.router,   prefix=settings.API_V1_STR)
app.include_router(system_api.router,    prefix=settings.API_V1_STR)

# Mount WebSocket Routers
app.include_router(voice.router,           prefix=settings.API_V1_STR)
app.include_router(connection.router,      prefix=settings.API_V1_STR, tags=["WebSocket Transport"])
app.include_router(voice_endpoints.router, prefix=settings.API_V1_STR)
app.include_router(voice_transport.router, prefix=settings.API_V1_STR)
