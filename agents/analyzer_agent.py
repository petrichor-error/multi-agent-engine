import json
from agents.base_agent import BaseAgent
from models.task import Task, AgentType


class AnalyzerAgent(BaseAgent):
    agent_type = AgentType.ANALYZER

    async def execute(self, task: Task) -> list[dict]:
        """
        Reads raw scraped data from shared memory, uses LLM to extract
        and structure the relevant items based on the original goal.
        """
        raw_data = self.queue.get_memory(self.workflow_id, "raw_scraped_data")

        if not raw_data:
            raise ValueError("No scraped data found in memory. Run ScraperAgent first.")

        # Combine all page text into one prompt
        combined_text = ""
        for item in raw_data:
            url = item.get("url", "")
            text = item.get("text", "")
            if text:
                combined_text += f"\n\n--- Source: {url} ---\n{text[:2000]}"

        structured_json = await self.ask_llm(
            system=(
                "You are a data extraction assistant. Given raw web page text "
                "and a user goal, extract the most relevant structured items. "
                "Return a JSON array of objects. Each object should have: "
                "'name', 'description', 'relevance_score' (1-10), and 'source_url'. "
                "Return only valid JSON, no explanation."
            ),
            user=f"Goal: {task.goal}\n\nRaw content:{combined_text}",
        )

        try:
            items = json.loads(structured_json)
        except Exception:
            items = [{"name": "Parse error", "description": structured_json,
                      "relevance_score": 0, "source_url": ""}]

        # Sort by relevance and keep top 10
        items = sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True)[:10]

        # Save to shared memory for summarizer
        self.queue.set_memory(self.workflow_id, "analyzed_items", items)
        return items