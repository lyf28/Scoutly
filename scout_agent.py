import os
import asyncio
from dotenv import load_dotenv
from browser_use import Agent
from browser_use.llm import ChatOpenAI
from config_loader import ConfigLoader

# Load environment variables (API Keys)
load_dotenv()

class ScoutAgent:
    def __init__(self, domain_config):
        self.config = domain_config
        # remove_min_items_from_schema=True strips the `minItems` constraint
        # from the AgentOutput JSON schema before sending to OpenAI.
        # OpenAI strict structured-output mode does not support minItems, so
        # keeping it causes every step to fail with an API schema error ("items").
        self.llm = ChatOpenAI(model="gpt-4o", remove_min_items_from_schema=True)

    async def run_discovery(self):
        """
        Phase 1: Discover articles and return structured JSON data.
        """
        source_url = self.config['sources'][0]['url']
        discovery_goal = self.config['scouting_logic']['discovery_goal']

        # arXiv article URLs are always https://arxiv.org/abs/{id} —
        # tell the agent to extract IDs and construct URLs directly,
        # so it never needs to click individual articles to find their links.
        task_description = (
            f"Go to {source_url}. "
            f"Look for any articles related to: {discovery_goal}. "
            "If you find ANY matching articles, extract up to 5. "
            "If no direct matches, extract the first 3 articles from the list. "
            "IMPORTANT: Each article has an arXiv ID like '2602.12345'. "
            "Construct each article URL as 'https://arxiv.org/abs/{arxiv_id}'. "
            "Do NOT click each article to find its URL — construct it directly. "
            "Return ONLY a JSON list with keys 'title' and 'url'. No extra text."
        )

        try:
            agent = Agent(
                task=task_description,
                llm=self.llm,
                use_vision=False,
                max_actions_per_step=1,
                use_judge=False,  # skip post-run LLM judge call (~30s saved)
            )
            history = await agent.run(max_steps=10)

            # Primary: agent explicitly called done() with a result
            result = history.final_result()

            # Fallback: agent ran out of steps without calling done —
            # try to recover JSON from the last extracted content
            if not result:
                extracted = history.extracted_content()
                if extracted:
                    result = extracted[-1]

            return result
        except Exception as e:
            raise Exception(f"Discovery failed: {str(e)}")

    async def run_summary(self, url: str):
        """
        Phase 2: Perform deep-dive summary for a specific URL.
        Utilizes the model's reasoning capabilities to analyze page content.
        """
        task_description = (
            f"Navigate to {url}. Read the main content of this page. "
            f"Provide a concise summary focusing on: {', '.join(self.config['scouting_logic']['focus_points'])}. "
            f"If there are technical diagrams or code snippets, please explain them. "
            f"IMPORTANT: Output the summary in Traditional Chinese with Markdown formatting."
        )

        try:
            agent = Agent(
                task=task_description,
                llm=self.llm,
                use_vision=False,
                max_actions_per_step=1,
                use_judge=False,  # skip post-run LLM judge call
            )
            history = await agent.run(max_steps=10)

            result = history.final_result()
            if not result:
                extracted = history.extracted_content()
                if extracted:
                    result = extracted[-1]

            return result
        except Exception as e:
            raise Exception(f"Summary failed: {str(e)}")

async def main():
    """
    Basic entry point for local testing.
    """
    loader = ConfigLoader()
    # Load AIOps configuration for testing
    try:
        aiops_cfg = loader.load_config("aiops")
        scout = ScoutAgent(aiops_cfg)
        print(f"--- Starting Discovery for {aiops_cfg['domain']} ---")
        
        result = await scout.run_discovery()
        print(f"Discovery Result:\n{result}")
        
    except Exception as e:
        print(f"Failed to run agent: {e}")

if __name__ == "__main__":
    # Use asyncio to run the async main function
    asyncio.run(main())