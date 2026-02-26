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
from ui_generator import generate_scout_flex, generate_summary_flex, generate_help_flex
from intent_parser import parse_intent

load_dotenv()

app = FastAPI()

# Initialize LINE API
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

async def run_agent_and_reply(user_id: str, config: dict):
    """
    Background task: run discovery with the given config and push the result.
    config may come from a YAML file or be dynamically built by intent_parser.
    """
    domain_label = config.get('domain', 'Custom')
    try:
        agent = ScoutAgent(config)
        result_json = await agent.run_discovery()

        if result_json is None:
            line_bot_api.push_message(user_id, TextSendMessage(text="查無相關結果，請換個關鍵字再試。"))
            return

        flex_msg = generate_scout_flex(domain_label.upper(), result_json,
                                       domain_key=config.get('_domain_key', 'aiops'))
        line_bot_api.push_message(user_id, flex_msg)
    except Exception as e:
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"❌ Scout error ({domain_label}): {str(e)}")
        )

async def run_summary_and_reply(user_id: str, url: str, domain_key: str = 'aiops'):
    """
    Background task: deep-dive a single article and push the summary.
    """
    try:
        loader = ConfigLoader()
        # Fall back to aiops focus points if domain_key isn't a known YAML
        try:
            config = loader.load_config(domain_key)
        except FileNotFoundError:
            config = loader.load_config('aiops')
        agent = ScoutAgent(config)
        summary = await agent.run_summary(url)
        line_bot_api.push_message(user_id, generate_summary_flex(summary))
    except Exception as e:
        line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ Summary Error: {str(e)}"))

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
    user_text = event.message.text.strip()
    user_id   = event.source.user_id

    # Help command
    if user_text.lower() in ('help', '/help', '說明', '使用說明'):
        loader = ConfigLoader()
        line_bot_api.reply_message(
            event.reply_token,
            generate_help_flex(loader.list_available_domains())
        )
        return

    # Parse intent with GPT-4o-mini (fast & cheap)
    try:
        config = parse_intent(user_text)
    except Exception as e:
        print(f"[intent_parser] error: {e}")
        config = None

    if config is None:
        # Not a scouting request — show help
        loader = ConfigLoader()
        line_bot_api.reply_message(
            event.reply_token,
            generate_help_flex(loader.list_available_domains())
        )
        return

    domain_label = config.get('domain', 'Custom')
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"🚀 正在搜尋：{domain_label}\n稍等一下，找到後會推播給你...")
    )
    asyncio.create_task(run_agent_and_reply(user_id, config))

@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent):
    """
    Handles button clicks from Flex Messages (Deep Dive).
    Postback data format: "action=summarize&domain=aiops&url=https://..."
    """
    from urllib.parse import parse_qs, urlencode
    user_id = event.source.user_id
    # Use parse_qs so URLs with '=' chars are handled correctly
    params = {k: v[0] for k, v in parse_qs(event.postback.data).items()}

    if params.get('action') == 'summarize':
        target_url  = params.get('url', '')
        domain_key  = params.get('domain', 'aiops')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🧠 正在分析文章，稍後會推播結果...")
        )
        asyncio.create_task(run_summary_and_reply(user_id, target_url, domain_key))

@app.get("/")
async def root():
    return {"status": "Service is running", "agent": "Scoutly Universal AI Scout"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)