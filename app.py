import os
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# Import our custom modules
from config_loader import ConfigLoader
from scout_agent import ScoutAgent

load_dotenv()

app = FastAPI()

# Initialize LINE API with environment variables
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.post("/callback")
async def run_agent_and_reply(user_id, reply_token, domain="aiops"):
    """
    Background task to run the agent and send the result via push message.
    """
    try:
        loader = ConfigLoader()
        config = loader.load_config(domain)
        agent = ScoutAgent(config)
        
        # This takes 30-60 seconds
        result = await agent.run_discovery()
        
        # After discovery, we use 'push_message' because the reply_token will expire
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"🔍 Scouting Report for {domain.upper()}:\n\n{result}")
        )
    except Exception as e:
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"❌ An error occurred: {str(e)}")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    user_id = event.source.user_id
    
    if user_text.lower() == "scout aiops":
        # 1. Reply immediately to satisfy LINE's timeout constraint
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🚀 Agent dispatched! I'll send you the report once it's ready.")
        )
        
        # 2. Start the agent in the background
        # We use the running event loop to create a background task
        loop = asyncio.get_event_loop()
        loop.create_task(run_agent_and_reply(user_id, event.reply_token))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Welcome! Type 'scout aiops' to start monitoring.")
        )