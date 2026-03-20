from abc import ABC, abstractmethod
from typing import Any
from openai import AsyncOpenAI
from config import settings
from models.task import Task, TaskResult, TaskStatus, AgentType
from queue.redis_queue import RedisQueue
import time


class BaseAgent(ABC):
    agent_type: AgentType

    def __init__(self, workflow_id: str, queue: RedisQueue):
        self.workflow_id = workflow_id
        self.queue = queue
        self.llm = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, task: Task) -> TaskResult:
        result = TaskResult(
            task_id=task.id,
            agent_type=self.agent_type,
            status=TaskStatus.RUNNING
        )
        self.queue.set_task_result(result)

        try:
            output = await self.execute(task)
            result.status = TaskStatus.DONE
            result.output = output
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
        finally:
            result.completed_at = time.time()
            self.queue.set_task_result(result)

        return result

    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """Each agent implements its own logic here."""
        ...

    async def ask_llm(self, system: str, user: str, model: str = "gpt-4o") -> str:
        response = await self.llm.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()