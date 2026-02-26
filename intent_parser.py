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
    Returns a config dict ready to pass into ScoutAgent, or None if the
    message is not a scouting request at all.

    The returned dict always has the same shape as a YAML domain config.
    """
    loader = ConfigLoader()
    available = loader.list_available_domains()  # e.g. ['aiops', 'stocks']

    system_prompt = (
        "You are a research assistant that extracts scouting intent from user messages.\n"
        "User may write in any language (Chinese, English, etc.).\n\n"
        "Reply with JSON only — no extra text. Format:\n"
        '{"is_scout_request": true/false, "topic": "<short English keyword>", '
        '"matched_domain": "<domain_key or null>", "search_query": "<2-sentence English arXiv search description>"}\n\n'
        f"Known domain keys: {available}\n"
        "Set matched_domain to the best matching key if the topic clearly maps to one, else null.\n"
        "If the message is not asking to find/research/scout anything, set is_scout_request=false."
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
    topic = parsed.get("topic", "AI research")
    search_query = parsed.get("search_query", f"Recent papers about {topic}.")

    return {
        "_domain_key": f"custom:{topic}",
        "domain": topic,
        "sources": [{"name": "arXiv", "url": "https://arxiv.org/search/?searchtype=all&query=" + topic.replace(" ", "+")}],
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
