import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent
from config_loader import ConfigLoader

# Load environment variables (API Keys)
load_dotenv()

class ScoutAgent:
    """
    The core agent responsible for navigating websites and extracting information.
    Leverages browser-use for autonomous web navigation.
    """
    def __init__(self, domain_config):
        self.config = domain_config
        # It's better to keep LLM version flexible
        self.llm = ChatOpenAI(model="gpt-4o")

    async def run_discovery(self):
        """
        Phase 1: Discover titles and links. 
        The agent reasons in English for precision but outputs in Traditional Chinese for users.
        """
        # Dynamically construct the prompt using domain configuration
        task_description = (
            f"Navigate to {self.config['sources'][0]['url']} and identify the latest articles "
            f"matching the goal: {self.config['scouting_logic']['discovery_goal']}. "
            f"Extract the top 5 article titles and their corresponding URLs. "
            f"IMPORTANT: Please provide the titles in Traditional Chinese."
        )

        try:
            agent = Agent(
                task=task_description,
                llm=self.llm,
            )
            # Run the agent and capture the result
            history = await agent.run()
            # In browser-use, history.final_result contains the LLM's last response
            return history.final_result()
        except Exception as e:
            return f"An error occurred during discovery: {str(e)}"

    async def run_summary(self, url: str):
        """
        Phase 2: Perform deep-dive summary for a specific URL with visual context.
        """
        # Placeholder for summary logic (to be implemented with Vision)
        summary_prompt = (
            f"Analyze the content at {url}. "
            f"Focus points: {', '.join(self.config['scouting_logic']['focus_points'])}. "
            f"Language: Traditional Chinese."
        )
        pass

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