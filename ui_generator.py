import re
import json
from urllib.parse import urlencode
from linebot.models import (
    FlexSendMessage, BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, PostbackAction,
    SeparatorComponent, URIAction, FillerComponent,
)

# ── Palette ───────────────────────────────────────────────────────────────────
C_NAVY    = '#0D1B2A'   # header bg
C_TEAL    = '#00C9A7'   # accent
C_TEAL_DK = '#00957C'   # button fill
C_PURPLE  = '#845EC2'   # help accent
C_WHITE   = '#FFFFFF'
C_OFF_W   = '#F5F7FA'   # card bg
C_LABEL   = '#8899AA'   # muted
C_BODY    = '#2D3748'   # body text
C_MUTED   = '#A0AEC0'   # secondary

# ── Scout Report (Carousel) ───────────────────────────────────────────────────

def generate_scout_flex(domain_name: str, articles_json_str: str,
                        domain_key: str = 'aiops') -> FlexSendMessage:
    """One bubble per article in a horizontal carousel."""
    try:
        articles = json.loads(articles_json_str)
        if not isinstance(articles, list):
            articles = []
    except (json.JSONDecodeError, TypeError):
        articles = []

    if not articles:
        from linebot.models import TextSendMessage
        return TextSendMessage(text='🔍 查無結果，請換個關鍵字再試。')

    bubbles = []
    total = len(articles[:5])
    for i, art in enumerate(articles[:5], start=1):
        title = art.get('title') or art.get('name') or 'Untitled Article'
        url   = art.get('url')   or art.get('link') or 'https://arxiv.org'
        postback_data = urlencode({'action': 'summarize', 'domain': domain_key, 'url': url})

        bubble = BubbleContainer(
            size='kilo',
            header=BoxComponent(
                layout='vertical',
                backgroundColor=C_NAVY,
                paddingAll='16px',
                contents=[
                    BoxComponent(
                        layout='horizontal',
                        contents=[
                            BoxComponent(
                                layout='vertical',
                                backgroundColor=C_TEAL,
                                cornerRadius='20px',
                                paddingStart='10px', paddingEnd='10px',
                                paddingTop='4px', paddingBottom='4px',
                                width='80px',
                                contents=[
                                    TextComponent(
                                        text=domain_name[:10],
                                        size='xxs', color=C_NAVY,
                                        weight='bold', align='center'
                                    )
                                ]
                            ),
                            FillerComponent(),
                            TextComponent(
                                text=f'{i}\u00a0/\u00a0{total}',
                                size='xxs', color=C_LABEL,
                                align='end', gravity='center'
                            ),
                        ]
                    ),
                ]
            ),
            body=BoxComponent(
                layout='vertical',
                backgroundColor=C_OFF_W,
                paddingAll='16px',
                contents=[
                    TextComponent(
                        text=title, size='sm', weight='bold',
                        color=C_BODY, wrap=True, maxLines=4
                    ),
                ]
            ),
            footer=BoxComponent(
                layout='horizontal',
                backgroundColor=C_OFF_W,
                paddingAll='12px',
                spacing='sm',
                contents=[
                    ButtonComponent(
                        style='secondary', height='sm', flex=1,
                        action=URIAction(label='開啟 ↗', uri=url)
                    ),
                    ButtonComponent(
                        style='primary', height='sm', flex=2,
                        color=C_TEAL_DK,
                        action=PostbackAction(label='🔬 Deep Dive', data=postback_data)
                    ),
                ]
            ),
        )
        bubbles.append(bubble)

    if len(bubbles) == 1:
        return FlexSendMessage(
            alt_text=f'🔍 {domain_name} — 找到 {total} 篇',
            contents=bubbles[0]
        )
    return FlexSendMessage(
        alt_text=f'🔍 {domain_name} — 找到 {total} 篇',
        contents=CarouselContainer(contents=bubbles)
    )



# ── Deep Dive Summary ─────────────────────────────────────────────────────────

def generate_summary_flex(summary_text: str) -> FlexSendMessage:
    """Dark-header bubble with teal left-bar section labels and bullet rows."""
    text = (summary_text or '').strip()

    title_match = re.search(r'^##\s+(.+)$', text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else 'Deep Dive Analysis'

    section_matches = list(re.finditer(r'^###\s+(.+)$', text, re.MULTILINE))
    sections = []
    for i, match in enumerate(section_matches):
        heading = match.group(1).strip()
        start   = match.end()
        end     = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(text)
        raw     = text[start:end].strip()
        raw     = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
        raw     = re.sub(r'\*(.+?)\*',     r'\1', raw)
        lines   = [l.strip() for l in raw.splitlines() if l.strip()]
        bullets = []
        for line in lines:
            if line.startswith('- '):
                bullets.append(line[2:])
            else:
                bullets.extend(s.strip() for s in re.split(r'[。\.]\s*', line) if s.strip())
        if bullets:
            sections.append((heading, bullets))

    body_rows = []
    for sec_i, (heading, bullets) in enumerate(sections):
        if sec_i > 0:
            body_rows.append(SeparatorComponent(margin='lg'))
        body_rows.append(
            BoxComponent(
                layout='horizontal',
                margin='lg',
                spacing='sm',
                contents=[
                    BoxComponent(
                        layout='vertical', width='4px',
                        backgroundColor=C_TEAL,
                        contents=[FillerComponent()]
                    ),
                    TextComponent(
                        text=heading, weight='bold', size='sm',
                        color=C_BODY, wrap=True, flex=1
                    ),
                ]
            )
        )
        for bullet in bullets:
            body_rows.append(
                BoxComponent(
                    layout='horizontal', margin='sm',
                    spacing='sm', paddingStart='8px',
                    contents=[
                        TextComponent(text='•', size='sm', color=C_TEAL, flex=0, gravity='top'),
                        TextComponent(text=bullet, size='sm', color=C_BODY, wrap=True, flex=1),
                    ]
                )
            )

    if not body_rows:
        cleaned = re.sub(r'#+\s*', '', text)
        cleaned = re.sub(r'\*+', '', cleaned)
        body_rows = [TextComponent(text=cleaned, size='sm', wrap=True, color=C_BODY)]

    bubble = BubbleContainer(
        size='giga',
        header=BoxComponent(
            layout='vertical',
            backgroundColor=C_NAVY,
            paddingAll='20px',
            spacing='sm',
            contents=[
                BoxComponent(
                    layout='vertical',
                    backgroundColor=C_TEAL,
                    cornerRadius='20px',
                    paddingStart='10px', paddingEnd='10px',
                    paddingTop='4px', paddingBottom='4px',
                    width='90px',
                    contents=[
                        TextComponent(
                            text='DEEP DIVE', size='xxs',
                            color=C_NAVY, weight='bold', align='center'
                        )
                    ]
                ),
                TextComponent(
                    text=title, weight='bold', size='md',
                    color=C_WHITE, wrap=True, margin='sm'
                ),
            ]
        ),
        body=BoxComponent(
            layout='vertical',
            backgroundColor=C_OFF_W,
            paddingAll='20px',
            contents=body_rows
        ),
    )
    return FlexSendMessage(alt_text='📝 Deep Dive Analysis', contents=bubble)


# ── Help / Welcome card ───────────────────────────────────────────────────────

def generate_help_flex(available_domains: list[str]) -> FlexSendMessage:
    """Welcome card: example chips + preset domain tags + tip."""

    example_chips = [
        '幫我找 AIOps 論文',
        '最新量子計算研究',
        'LLM agent papers',
        'drug discovery AI',
    ]

    chip_rows = [
        BoxComponent(
            layout='vertical',
            backgroundColor='#EEF2FF',
            cornerRadius='8px',
            paddingAll='10px',
            margin='sm',
            contents=[
                TextComponent(text=f'💬  {ex}', size='sm', color=C_PURPLE, wrap=True)
            ]
        )
        for ex in example_chips
    ]

    domain_tags = [
        BoxComponent(
            layout='vertical',
            backgroundColor=C_TEAL,
            cornerRadius='20px',
            paddingStart='12px', paddingEnd='12px',
            paddingTop='5px', paddingBottom='5px',
            contents=[
                TextComponent(text=d.upper(), size='xxs', color=C_NAVY,
                              weight='bold', align='center')
            ]
        )
        for d in available_domains
    ]

    bubble = BubbleContainer(
        size='giga',
        header=BoxComponent(
            layout='vertical',
            backgroundColor=C_NAVY,
            paddingAll='20px',
            spacing='xs',
            contents=[
                TextComponent(text='🤖  Scoutly', weight='bold', size='xxl', color=C_WHITE),
                TextComponent(text='你的 AI 研究情報官', size='sm', color=C_LABEL),
            ]
        ),
        body=BoxComponent(
            layout='vertical',
            backgroundColor=C_OFF_W,
            paddingAll='20px',
            spacing='lg',
            contents=[
                TextComponent(text='直接說你想找什麼就好 ↓',
                              size='sm', weight='bold', color=C_BODY),
                *chip_rows,
                SeparatorComponent(margin='lg'),
                TextComponent(text='已設定的主題', size='sm', weight='bold',
                              color=C_BODY, margin='lg'),
                BoxComponent(
                    layout='horizontal', margin='sm', spacing='sm',
                    contents=domain_tags
                ),
                SeparatorComponent(margin='lg'),
                BoxComponent(
                    layout='horizontal', margin='sm', spacing='sm',
                    contents=[
                        TextComponent(text='💡', size='sm', flex=0),
                        TextComponent(
                            text='任何主題都可以說，會自動幫你搜尋 arXiv。',
                            size='xs', color=C_MUTED, wrap=True, flex=1
                        ),
                    ]
                ),
            ]
        ),
    )
    return FlexSendMessage(alt_text='🤖 Scoutly — 歡迎使用', contents=bubble)
