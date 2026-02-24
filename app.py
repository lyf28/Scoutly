import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, PostbackEvent
from dotenv import load_dotenv

# Import our custom modules
from config_loader import ConfigLoader
from scout_agent import ScoutAgent
from ui_generator import generate_scout_flex

load_dotenv()

app = FastAPI()

# Initialize LINE API
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

async def run_agent_and_reply(user_id: str, domain: str = "aiops"):
    """
    Background task to run the agent and send the result via push message.
    """
    try:
        loader = ConfigLoader()
        config = loader.load_config(domain)
        agent = ScoutAgent(config)
        
        # Phase 1: Discovery (Returns JSON string)
        result_json = await agent.run_discovery()
        
        # Convert JSON to Flex Message UI
        flex_msg = generate_scout_flex(domain.upper(), result_json)
        
        # Push the elegant UI to the user
        line_bot_api.push_message(user_id, flex_msg)
    except Exception as e:
        line_bot_api.push_message(
            user_id, 
            TextSendMessage(text=f"❌ Error during {domain} scouting: {str(e)}")
        )

@app.post("/callback")
async def callback(request: Request):
    """
    Main entry point for LINE webhook events.
    """
    signature = request.headers.get('X-Line-Signature')
    body = await request.body()
    
    try:
        handler.handle(body.decode('utf-8'), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """
    Handles user text commands.
    """
    user_text = event.message.text
    user_id = event.source.user_id
    
    if user_text.lower() == "scout aiops":
        # Reply immediately to avoid LINE timeout
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🚀 Agent dispatched! I'll send you the report once it's ready.")
        )
        # Offload the heavy work to a background task
        asyncio.create_task(run_agent_and_reply(user_id, "aiops"))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Welcome! Type 'scout aiops' to start monitoring.")
        )

# NOTE: We will add @handler.add(PostbackEvent) here in the next step to handle "Deep Dive" buttons

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)