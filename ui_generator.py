from linebot.models import FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ButtonComponent, PostbackAction

def generate_scout_flex(domain_name, articles_json_str):
    """
    Generate a LINE Flex Message from the structured JSON data.
    """
    import json
    articles = json.loads(articles_json_str)
    
    bubbles = []
    for item in articles:
        title = item.get('title', 'Untitled Paper') 
        url = item.get('url') or item.get('link') or "https://arxiv.org"
    
    # Create list items for the Flex Message
    contents = []
    for art in articles:
        item = BoxComponent(
            layout='vertical',
            margin='lg',
            contents=[
                TextComponent(text=art['title'], weight='bold', size='md', wrap=True),
                ButtonComponent(
                    style='link',
                    height='sm',
                    action=PostbackAction(
                        label='深入了解 (Deep Dive)',
                        data=f"action=summarize&url={art['url']}"
                    )
                )
            ]
        )
        contents.append(item)

    # Wrap in a Bubble container
    bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[TextComponent(text=f"🔍 {domain_name} Report", weight='bold', size='xl')]
        ),
        body=BoxComponent(layout='vertical', contents=contents)
    )
    
    return FlexSendMessage(alt_text=f"{domain_name} Report", contents=bubble)