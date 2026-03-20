from agents.base_agent import BaseAgent
from models.task import Task, AgentType


class SummarizerAgent(BaseAgent):
    agent_type = AgentType.SUMMARIZER

    async def execute(self, task: Task) -> str:
        """
        Reads structured items from shared memory and produces a
        clean, human-readable summary using GPT-4o.
        """
        items = self.queue.get_memory(self.workflow_id, "analyzed_items")

        if not items:
            raise ValueError("No analyzed items found in memory. Run AnalyzerAgent first.")

        items_text = ""
        for i, item in enumerate(items, 1):
            items_text += (
                f"\n{i}. {item.get('name', 'Unknown')}\n"
                f"   Description: {item.get('description', '')}\n"
                f"   Relevance: {item.get('relevance_score', 'N/A')}/10\n"
                f"   Source: {item.get('source_url', '')}\n"
            )

        summary = await self.ask_llm(
            system=(
                "You are a concise research assistant. Given a list of structured "
                "results and the user's original goal, write a clear, well-formatted "
                "summary in plain English. Use bullet points where helpful. "
                "Be direct and informative — no filler phrases."
            ),
            user=f"Goal: {task.goal}\n\nItems found:{items_text}",
        )

        # Save final result to shared memory
        self.queue.set_memory(self.workflow_id, "final_summary", summary)
        return summary