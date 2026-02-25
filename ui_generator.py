from linebot.models import FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ButtonComponent, PostbackAction

def generate_scout_flex(domain_name, articles_json_str):
    """
    Generate a LINE Flex Message from the structured JSON data.
    """
    import json

    # Safely parse – handle both raw JSON list and wrapped strings
    try:
        articles = json.loads(articles_json_str)
    except (json.JSONDecodeError, TypeError):
        articles = []

    if not articles:
        from linebot.models import TextSendMessage
        return TextSendMessage(text="No results found. Please try again later.")

    # Create list items for the Flex Message
    contents = []
    for art in articles:
        # Use .get() with safe fallbacks to prevent KeyError
        title = art.get('title') or art.get('name') or 'Untitled Article'
        url = art.get('url') or art.get('link') or 'https://arxiv.org'

        item = BoxComponent(
            layout='vertical',
            margin='lg',
            contents=[
                TextComponent(text=title, weight='bold', size='md', wrap=True),
                ButtonComponent(
                    style='link',
                    height='sm',
                    action=PostbackAction(
                        label='Deep Dive ➜',
                        data=f"action=summarize&url={url}"
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