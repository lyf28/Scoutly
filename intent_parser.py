"""
intent_parser.py
Translates free-form user messages into a (domain_key, config_dict) pair.

Flow:
  1. Use GPT to extract a topic/keyword from the user's message.
  2. Try to match it to an existing YAML config (fuzzy).
  3. If no match, build a minimal dynamic config targeting arXiv.
"""

import json
import os
from openai import OpenAI
from config_loader import ConfigLoader

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def parse_intent(user_text: str) -> dict | None:
    """
    Returns a config dict ready to pass into ScoutAgent, or None only for
    pure greetings / thank-you / uninterpretable messages.

    Design principle: be aggressive — if there is ANY noun/topic in the
    message, treat it as a scout request and search arXiv for it.
    """
    loader = ConfigLoader()
    available = loader.list_available_domains()  # e.g. ['aiops', 'stocks']

    system_prompt = (
        "You are a research topic extractor for an AI paper scouting bot.\n"
        "The user sends a message in any language. Your job:\n"
        "1. Decide if there is ANY topic worth searching — be VERY generous.\n"
        "   Only set is_scout_request=false for pure greetings (hi/hello/謝謝/你好),\n"
        "   empty messages, or messages that are clearly not about any subject.\n"
        "2. Extract the core English keyword(s) for the topic.\n"
        "3. Write a 1-2 sentence English arXiv search description.\n\n"
        "Reply with JSON only — no extra text. Format:\n"
        '{"is_scout_request": true/false, "topic": "<short English keyword(s)>", '
        '"matched_domain": "<domain_key or null>", '
        '"search_query": "<1-2 sentence arXiv search description>"}\n\n'
        f"Known domain keys (use if topic clearly matches): {available}\n"
        "Examples of is_scout_request=true: '量子計算', 'transformer architecture',\n"
        "'2024 LLM papers', '幫我找強化學習', 'latest GPU research', 'drug discovery AI'\n"
        "Examples of is_scout_request=false: '你好', 'hello', '謝謝', 'ok', '好的'"
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text},
        ],
        temperature=0,
    )

    try:
        parsed = json.loads(response.choices[0].message.content)
    except Exception:
        return None

    if not parsed.get("is_scout_request"):
        return None

    # If it maps to a known YAML config, use that
    matched = parsed.get("matched_domain")
    if matched and matched in available:
        return {"_domain_key": matched, **loader.load_config(matched)}

    # Otherwise build a dynamic config for arXiv search
    topic = parsed.get("topic") or user_text[:60]
    search_query = parsed.get("search_query") or f"Recent papers about {topic}."
    arxiv_query = topic.replace(" ", "+")

    return {
        "_domain_key": f"custom:{topic}",
        "domain": topic,
        "sources": [{
            "name": "arXiv",
            "url": f"https://arxiv.org/search/?searchtype=all&query={arxiv_query}&order=-announced_date_first"
        }],
        "scouting_logic": {
            "discovery_goal": search_query,
            "summary_depth": "detailed",
            "focus_points": [
                "Core technical contribution",
                "Problem being solved",
                "Key results or findings",
            ],
        },
        "ui_display": {"color_code": "#7B61FF", "icon": "🔬"},
    }
