import re
import json
from urllib.parse import urlencode
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, PostbackAction, SeparatorComponent, URIAction
)

def generate_scout_flex(domain_name: str, articles_json_str: str, domain_key: str = 'aiops'):
    """
    Generate a LINE Flex Message from the structured JSON data.
    """
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
        url   = art.get('url')   or art.get('link') or 'https://arxiv.org'

        # Embed domain_key so Deep Dive uses the right focus points
        postback_data = urlencode({'action': 'summarize', 'domain': domain_key, 'url': url})

        item = BoxComponent(
            layout='vertical',
            margin='lg',
            spacing='sm',
            contents=[
                TextComponent(text=title, weight='bold', size='sm', wrap=True),
                BoxComponent(
                    layout='horizontal',
                    contents=[
                        ButtonComponent(
                            style='link', height='sm', flex=1,
                            action=URIAction(label='開啟 ↗', uri=url)
                        ),
                        ButtonComponent(
                            style='primary', height='sm', flex=1,
                            color='#1A6B72',
                            action=PostbackAction(label='Deep Dive ➜', data=postback_data)
                        ),
                    ]
                )
            ]
        )
        contents.append(item)
        contents.append(SeparatorComponent(margin='md'))

    # Remove trailing separator
    if contents and isinstance(contents[-1], SeparatorComponent):
        contents.pop()

    bubble = BubbleContainer(
        size='giga',
        header=BoxComponent(
            layout='vertical',
            backgroundColor='#1A6B72',
            paddingAll='lg',
            contents=[TextComponent(text=f'🔍 {domain_name} Scout Report',
                                    weight='bold', size='lg', color='#ffffff')]
        ),
        body=BoxComponent(layout='vertical', paddingAll='lg', contents=contents)
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
        # Section heading
        body_contents.append(
            TextComponent(text=heading, weight='bold', size='sm', color='#1A6B72', margin='lg')
        )
        # Parse bullets if present, otherwise split by sentence
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        bullets = []
        for line in lines:
            if line.startswith('- '):
                bullets.append(line[2:])
            elif line:
                # split prose by Chinese period or newline into short chunks
                bullets.extend([s.strip() for s in re.split(r'[。\.]\s*', line) if s.strip()])

        for bullet in bullets:
            body_contents.append(
                BoxComponent(
                    layout='horizontal',
                    margin='sm',
                    contents=[
                        TextComponent(text='·', size='sm', color='#1A6B72',
                                      flex=0, gravity='top'),
                        TextComponent(text=bullet, size='sm', wrap=True,
                                      color='#333333', margin='sm', flex=1)
                    ]
                )
            )

    # Fallback if no sections parsed
    if not body_contents:
        cleaned = re.sub(r'#+\s*', '', text)
        cleaned = re.sub(r'\*+', '', cleaned)
        body_contents = [TextComponent(text=cleaned, size='sm', wrap=True)]

    bubble = BubbleContainer(
        size='giga',
        header=BoxComponent(
            layout='vertical',
            backgroundColor='#1A6B72',
            paddingAll='lg',
            contents=[
                TextComponent(text='📝 Deep Dive', size='xs', color='#ffffffaa'),
                TextComponent(
                    text=title, weight='bold', size='sm',
                    color='#ffffff', wrap=True, margin='sm'
                )
            ]
        ),
        body=BoxComponent(
            layout='vertical',
            paddingAll='lg',
            spacing='md',
            contents=body_contents
        )
    )

    return FlexSendMessage(alt_text='Deep Dive Analysis', contents=bubble)


def generate_help_flex(available_domains: list[str]) -> FlexSendMessage:
    """
    Welcome / help card shown when user sends 'help' or an unrecognised message.
    """
    domain_rows = []
    for d in available_domains:
        domain_rows.append(
            BoxComponent(
                layout='horizontal',
                margin='sm',
                contents=[
                    TextComponent(text='·', size='sm', color='#7B61FF', flex=0),
                    TextComponent(text=d.upper(), size='sm', weight='bold',
                                  color='#333333', margin='sm', flex=1),
                ]
            )
        )

    bubble = BubbleContainer(
        size='giga',
        header=BoxComponent(
            layout='vertical',
            backgroundColor='#7B61FF',
            paddingAll='lg',
            contents=[
                TextComponent(text='🤖 Scoutly', weight='bold', size='xl', color='#ffffff'),
                TextComponent(text='AI Research Scout', size='xs', color='#ffffffaa', margin='sm'),
            ]
        ),
        body=BoxComponent(
            layout='vertical',
            paddingAll='lg',
            spacing='md',
            contents=[
                TextComponent(text='你可以這樣說：', weight='bold', size='sm', color='#7B61FF'),
                TextComponent(
                    text='「幫我找 AIOps 相關論文」\n「最新量子計算研究」\n「scout stocks」\n"find papers on LLM agents"',
                    size='sm', wrap=True, color='#444444', margin='sm'
                ),
                SeparatorComponent(margin='lg'),
                TextComponent(text='已設定的領域：', weight='bold', size='sm',
                              color='#7B61FF', margin='lg'),
                *domain_rows,
                SeparatorComponent(margin='lg'),
                TextComponent(
                    text='任何自訂主題也可以直接說，會自動搜尋 arXiv。',
                    size='xs', wrap=True, color='#888888', margin='lg'
                ),
            ]
        )
    )
    return FlexSendMessage(alt_text='Scoutly Help', contents=bubble)