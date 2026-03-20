from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from agents.base_agent import BaseAgent
from models.task import Task, AgentType


class ScraperAgent(BaseAgent):
    agent_type = AgentType.SCRAPER

    async def execute(self, task: Task) -> list[dict]:
        """
        Uses LLM to decide what URLs to scrape based on the goal,
        then scrapes them with Playwright and returns raw text chunks.
        """
        # Step 1: Ask LLM to generate search URLs from the goal
        urls_raw = await self.ask_llm(
            system=(
                "You are a research assistant. Given a goal, return 3 relevant "
                "public URLs to scrape for information. Return only a JSON array "
                "of URL strings, nothing else."
            ),
            user=f"Goal: {task.goal}",
            model="gpt-4o-mini",
        )

        import json
        try:
            urls = json.loads(urls_raw)
        except Exception:
            urls = []

        # Store URLs in shared memory for other agents to reference
        self.queue.set_memory(self.workflow_id, "scraped_urls", urls)

        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for url in urls[:3]:
                try:
                    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Remove noise
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()

                    text = soup.get_text(separator=" ", strip=True)
                    # Trim to avoid blowing up the context window
                    results.append({"url": url, "text": text[:4000]})
                except Exception as e:
                    results.append({"url": url, "text": "", "error": str(e)})

            await browser.close()

        # Save raw results to shared memory
        self.queue.set_memory(self.workflow_id, "raw_scraped_data", results)
        return results