import os
import asyncio
import langchain_core
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent
from config_loader import ConfigLoader
from pydantic import Field

# Load environment variables (API Keys)
load_dotenv()

class ScoutAgent:
    def __init__(self, domain_config):
        self.config = domain_config
        
        real_llm = ChatOpenAI(model="gpt-4o")
        
        class LLMProxy:
            def __init__(self, llm):
                self.llm = llm
                self.provider = "openai"

            def __getattr__(self, name):
                return getattr(self.llm, name)

        self.llm = LLMProxy(real_llm)

    async def run_discovery(self):
        """
        Phase 1: Discover articles and return structured JSON data.
        """
        source_url = self.config['sources'][0]['url']
        discovery_goal = self.config['scouting_logic']['discovery_goal']

        # Force the LLM to return a valid JSON list of dictionaries
        task_description = (
            f"Go to {source_url}. "
            f"Look for any articles that might be related to: {discovery_goal}. "
            "If you find ANY articles, extract at least 3. "
            "If no direct matches, extract the first 3 latest articles from the list. "
            "Format the result as a JSON list of objects with EXACTLY two keys: 'title' and 'url'. "
            "The 'title' MUST be in English. "
            "The 'url' MUST be a valid absolute URL starting with 'https://'. "
            "Return ONLY the JSON list, no extra text."
        )

        try:
            agent = Agent(task=task_description, llm=self.llm)
            history = await agent.run(max_steps=15)

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
            agent = Agent(task=task_description, llm=self.llm)
            history = await agent.run(max_steps=15)

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