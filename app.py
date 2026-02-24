import os
import asyncio
import subprocess
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
        
        line_bot_api.push_message(user_id, flex_msg)
    except Exception as e:
        line_bot_api.push_message(
            user_id, 
            TextSendMessage(text=f"❌ Error during {domain} scouting: {str(e)}")
        )

async def run_summary_and_reply(user_id: str, url: str):
    """
    Background task to analyze a specific article and push the summary.
    """
    try:
        loader = ConfigLoader()
        config = loader.load_config("aiops")
        agent = ScoutAgent(config)
        
        # Phase 2: Deep Dive (Uses Vision/LLM reasoning)
        summary = await agent.run_summary(url)
        
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"📝 **Deep Dive Analysis**\n\n{summary}")
        )
    except Exception as e:
        line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ Summary Error: {str(e)}"))

@app.on_event("startup")
async def startup_event():
    """
    Ensure Playwright browsers are installed on startup.
    This handles cases where the build cache might be inconsistent.
    """
    try:
        print("Checking Playwright browsers...")
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("Playwright browsers are ready.")
    except Exception as e:
        print(f"Failed to install browsers: {e}")

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
def handle_message(event: MessageEvent):
    user_text = event.message.text.lower()
    user_id = event.source.user_id
    
    # Dynamic domain matching: "scout aiops" or "scout stocks"
    if user_text.startswith("scout "):
        target_domain = user_text.split(" ")[1] # Extract 'aiops' or 'stocks'
        
        try:
            # Pre-check if config exists
            loader = ConfigLoader()
            if target_domain in loader.list_available_domains():
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"🚀 Dispatching {target_domain.upper()} Agent...")
                )
                asyncio.create_task(run_agent_and_reply(user_id, target_domain))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"❌ Domain '{target_domain}' not supported yet.")
                )
        except Exception as e:
            print(f"Error: {e}")

@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent):
    """
    Handles button clicks from Flex Messages (Deep Dive).
    """
    user_id = event.source.user_id
    postback_data = event.postback.data # e.g., "action=summarize&url=https://..."
    
    params = dict(item.split('=') for item in postback_data.split('&'))
    
    if params.get('action') == 'summarize':
        target_url = params.get('url')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🧠 Analyzing the article... This may take a minute.")
        )
        asyncio.create_task(run_summary_and_reply(user_id, target_url))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)