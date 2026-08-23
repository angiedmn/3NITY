from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from celery.result import AsyncResult

# Import your Celery app, task, and Pydantic schema
from app.tasks.celery_app import app as celery_app
from app.tasks.worker import audit_company_task
from app.schemas.company import CompanyPayload

app = FastAPI(
    title="The Mirage Engine API",
    version="0.1.0",
    description="Corporate Substance Auditor"
)

# --- SECURITY SETUP ---
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    # This is your secret hackathon password
    if api_key != "mirage_admin_999":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Invalid API Key."
        )
    return api_key

# --- ENDPOINTS ---

@app.post("/audit")
def audit_company(payload: CompanyPayload, key: str = Depends(verify_api_key)):
    """
    Submits a company payload to the background Celery worker.
    Requires a valid X-API-Key header.
    """
    # Convert the Pydantic model to a standard JSON-compatible dictionary 
    # so Celery doesn't crash on HttpUrl objects
    task_payload = payload.model_dump(mode='json')
    task = audit_company_task.delay(task_payload)
    
    return {"message": "Audit started", "task_id": task.id}

@app.get("/audit/result/{task_id}")
def get_audit_result(task_id: str):
    """Fetches the reality index score from Redis using the task_id."""
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        "status": task_result.state,
        "result": task_result.result if task_result.state == "SUCCESS" else {}
    }