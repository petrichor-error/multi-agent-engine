import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models.task import WorkflowRequest, WorkflowResult, TaskStatus
from queue.redis_queue import RedisQueue
from orchestrator import Orchestrator

app = FastAPI(
    title="Multi-Agent Workflow Engine",
    description="Give it a goal. It figures out the rest.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

queue = RedisQueue()


@app.get("/")
def root():
    return {
        "name": "Multi-Agent Workflow Engine",
        "status": "running",
        "redis": "connected" if queue.ping() else "disconnected",
    }


@app.post("/run", response_model=dict)
async def run_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """
    Kick off a new workflow. Returns a workflow_id immediately.
    The agents run in the background — poll /result/{workflow_id} for updates.
    """
    orchestrator = Orchestrator()

    # Run in background so the API returns immediately
    async def _run():
        await orchestrator.run(request.goal)

    background_tasks.add_task(_run)

    # We need the workflow_id before the background task runs.
    # Re-create the orchestrator just to get the ID, then let the task run.
    # Simple approach: run inline for small goals (swap for true async queue in prod)
    workflow_id = await orchestrator.run(request.goal)

    return {
        "workflow_id": workflow_id,
        "message": "Workflow started. Poll /result/{workflow_id} for updates.",
        "goal": request.goal,
    }


@app.get("/result/{workflow_id}", response_model=WorkflowResult)
def get_result(workflow_id: str):
    """
    Poll this endpoint to check workflow status and get the final result.
    """
    result = queue.get_workflow(workflow_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return result


@app.get("/health")
def health():
    return {"redis": queue.ping()}