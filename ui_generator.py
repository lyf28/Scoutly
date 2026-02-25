import re
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, PostbackAction, SeparatorComponent
)

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


def generate_summary_flex(summary_text: str) -> FlexSendMessage:
    """
    Convert the markdown summary from run_summary() into a LINE Flex Message.
    Parses ## title and ### section headings into styled components.
    """
    text = (summary_text or '').strip()

    # Extract top-level title (## ...)
    title_match = re.search(r'^##\s+(.+)$', text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else 'Deep Dive Analysis'

    # Split into sections by ### headings
    section_matches = list(re.finditer(r'^###\s+(.+)$', text, re.MULTILINE))
    sections = []
    for i, match in enumerate(section_matches):
        heading = match.group(1).strip()
        start = match.end()
        end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(text)
        body = text[start:end].strip()
        body = re.sub(r'\*\*(.+?)\*\*', r'\1', body)  # strip **bold**
        body = re.sub(r'\*(.+?)\*', r'\1', body)      # strip *italic*
        if body:
            sections.append((heading, body))

    # Build body components
    body_contents = []
    for i, (heading, body) in enumerate(sections):
        if i > 0:
            body_contents.append(SeparatorComponent(margin='lg'))
        body_contents.append(
            TextComponent(text=heading, weight='bold', size='sm', color='#27ACB2', margin='lg')
        )
        body_contents.append(
            TextComponent(text=body, size='sm', wrap=True, margin='sm', color='#444444')
        )

    # Fallback if no sections parsed
    if not body_contents:
        cleaned = re.sub(r'#+\s*', '', text)  # strip heading markers
        cleaned = re.sub(r'\*+', '', cleaned)  # strip asterisks
        body_contents = [TextComponent(text=cleaned, size='sm', wrap=True)]

    bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            backgroundColor='#27ACB2',
            paddingAll='lg',
            contents=[
                TextComponent(text='📝 Deep Dive', size='xs', color='#ffffff80'),
                TextComponent(
                    text=title, weight='bold', size='md',
                    color='#ffffff', wrap=True, margin='sm'
                )
            ]
        ),
        body=BoxComponent(
            layout='vertical',
            paddingAll='lg',
            contents=body_contents
        )
    )

    return FlexSendMessage(alt_text='Deep Dive Analysis', contents=bubble)