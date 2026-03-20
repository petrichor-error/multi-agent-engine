import uuid
from models.task import Task, AgentType, WorkflowResult, TaskStatus
from queue.redis_queue import RedisQueue
from agents.scraper_agent import ScraperAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.summarizer_agent import SummarizerAgent


class Orchestrator:
    """
    Breaks a user goal into sequential tasks and runs the right
    agent for each one. Stores progress in Redis so the API
    can poll for results.
    """

    def __init__(self):
        self.queue = RedisQueue()

    async def run(self, goal: str) -> str:
        workflow_id = str(uuid.uuid4())

        # Register workflow as pending
        self.queue.set_workflow(workflow_id, WorkflowResult(
            workflow_id=workflow_id,
            status=TaskStatus.PENDING,
            goal=goal,
        ))

        try:
            self.queue.set_workflow(workflow_id, WorkflowResult(
                workflow_id=workflow_id,
                status=TaskStatus.RUNNING,
                goal=goal,
            ))

            # --- Stage 1: Scrape ---
            scraper = ScraperAgent(workflow_id, self.queue)
            scrape_task = Task(goal=goal, agent_type=AgentType.SCRAPER)
            scrape_result = await scraper.run(scrape_task)

            if scrape_result.status == TaskStatus.FAILED:
                raise Exception(f"Scraper failed: {scrape_result.error}")

            # --- Stage 2: Analyze ---
            analyzer = AnalyzerAgent(workflow_id, self.queue)
            analyze_task = Task(goal=goal, agent_type=AgentType.ANALYZER)
            analyze_result = await analyzer.run(analyze_task)

            if analyze_result.status == TaskStatus.FAILED:
                raise Exception(f"Analyzer failed: {analyze_result.error}")

            # --- Stage 3: Summarize ---
            summarizer = SummarizerAgent(workflow_id, self.queue)
            summarize_task = Task(goal=goal, agent_type=AgentType.SUMMARIZER)
            summarize_result = await summarizer.run(summarize_task)

            if summarize_result.status == TaskStatus.FAILED:
                raise Exception(f"Summarizer failed: {summarize_result.error}")

            final_summary = summarize_result.output

            self.queue.set_workflow(workflow_id, WorkflowResult(
                workflow_id=workflow_id,
                status=TaskStatus.DONE,
                goal=goal,
                result=final_summary,
            ))

        except Exception as e:
            self.queue.set_workflow(workflow_id, WorkflowResult(
                workflow_id=workflow_id,
                status=TaskStatus.FAILED,
                goal=goal,
                error=str(e),
            ))

        return workflow_id