from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid
import time


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AgentType(str, Enum):
    SCRAPER = "scraper"
    ANALYZER = "analyzer"
    SUMMARIZER = "summarizer"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    agent_type: AgentType
    input_data: Any = None
    created_at: float = Field(default_factory=time.time)


class TaskResult(BaseModel):
    task_id: str
    agent_type: AgentType
    status: TaskStatus
    output: Any = None
    error: str | None = None
    completed_at: float | None = None


class WorkflowRequest(BaseModel):
    goal: str


class WorkflowResult(BaseModel):
    workflow_id: str
    status: TaskStatus
    goal: str
    result: str | None = None
    error: str | None = None