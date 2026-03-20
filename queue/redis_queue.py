import json
import redis
from config import settings
from models.task import TaskResult, WorkflowResult


class RedisQueue:
    def __init__(self):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return self.client.ping()
        except Exception:
            return False

    # --- Workflow state ---

    def set_workflow(self, workflow_id: str, data: WorkflowResult) -> None:
        self.client.setex(
            f"workflow:{workflow_id}",
            3600,  # TTL: 1 hour
            data.model_dump_json()
        )

    def get_workflow(self, workflow_id: str) -> WorkflowResult | None:
        raw = self.client.get(f"workflow:{workflow_id}")
        if not raw:
            return None
        return WorkflowResult.model_validate_json(raw)

    # --- Task results ---

    def set_task_result(self, result: TaskResult) -> None:
        self.client.setex(
            f"task:{result.task_id}",
            3600,
            result.model_dump_json()
        )

    def get_task_result(self, task_id: str) -> TaskResult | None:
        raw = self.client.get(f"task:{task_id}")
        if not raw:
            return None
        return TaskResult.model_validate_json(raw)

    # --- Shared agent memory (key-value scratchpad) ---

    def set_memory(self, workflow_id: str, key: str, value: any) -> None:
        self.client.hset(f"memory:{workflow_id}", key, json.dumps(value))
        self.client.expire(f"memory:{workflow_id}", 3600)

    def get_memory(self, workflow_id: str, key: str) -> any:
        raw = self.client.hget(f"memory:{workflow_id}", key)
        return json.loads(raw) if raw else None

    def get_all_memory(self, workflow_id: str) -> dict:
        data = self.client.hgetall(f"memory:{workflow_id}")
        return {k: json.loads(v) for k, v in data.items()}