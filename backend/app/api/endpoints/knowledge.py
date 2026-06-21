from fastapi import APIRouter, BackgroundTasks, status
from app.core.logger import api_logger, knowledge_logger

router = APIRouter()

def run_workspace_ingestion():
    knowledge_logger.info("Executing background workspace markdown ingestion process")

@router.post("/knowledge/ingest", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    api_logger.info("Received request to trigger workspace RAG ingestion")
    background_tasks.add_task(run_workspace_ingestion)
    return {"message": "Workspace ingestion triggered successfully in the background."}
