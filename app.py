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
async def callback(request: Request):
    """
    Webhook endpoint for LINE to send events.
    Verifies the signature to ensure requests are from LINE.
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
    Handle incoming text messages from users.
    """
    user_text = event.message.text
    
    # Simple logic to trigger the agent
    if user_text.lower() == "scout aiops":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Agent is starting to scout AIOps... Please wait.")
        )
        # TODO: Integration with ScoutAgent in async manner
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"You said: {user_text}\nType 'scout aiops' to start.")
        )

if __name__ == "__main__":
    import uvicorn
    # Run the server locally on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)