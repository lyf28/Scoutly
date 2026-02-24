import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent
from config_loader import ConfigLoader

# Load environment variables (API Keys)
load_dotenv()

class ScoutAgent:
    def __init__(self, domain_config):
        self.config = domain_config
        # Initialize the LLM
        llm = ChatOpenAI(model="gpt-4o")
        
        # --- Fix for 'ChatOpenAI' object has no attribute 'provider' ---
        # Manually inject the provider attribute that browser-use expects
        if not hasattr(llm, 'provider'):
            llm.provider = 'openai' 
        # --------------------------------------------------------------
        
        self.llm = llm

    async def run_discovery(self):
        """
        Phase 1: Discover articles and return structured JSON data.
        """
        # Force the LLM to return a valid JSON list of dictionaries
        task_description = (
            f"Navigate to {self.config['sources'][0]['url']} and find the latest articles "
            f"related to: {self.config['scouting_logic']['discovery_goal']}. "
            "Extract the top 5 articles. "
            "Return the result ONLY as a JSON list with keys: 'title' and 'url'. "
            "The 'title' MUST be in Traditional Chinese."
        )

        try:
            agent = Agent(task=task_description, llm=self.llm)
            history = await agent.run()
            # The result is now a string representing a JSON list
            return history.final_result()
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
            # Using browser-use to analyze the page
            agent = Agent(task=task_description, llm=self.llm)
            history = await agent.run()
            return history.final_result()
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