#!/usr/bin/env python3
"""ask_george.py — Ask George a question, post answer to Teams."""

import os
import sys
import json
import datetime
import urllib.request
from pathlib import Path

def _load_env() -> None:
    """Load ~/.george/.env (KEY="value" lines) without overriding real env vars."""
    p = Path.home() / ".george" / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

ONELLM_API_KEY = os.environ.get("ONELLM_API_KEY", "")
TEAMS_WEBHOOK = os.environ.get("TEAMS_WEBHOOK", "")
ONELLM_URL = "https://apicid-dev.servicenow.com/v4/onellm/models/anthropic?model=claude-opus-4-6"
MEMORY_FILE = Path.home() / ".george" / "memory.json"

GEORGE_SYSTEM = """You are George — Theodore Simmons' personal AI intelligence analyst at ServiceNow.
You have deep Anthropic knowledge and reason from their worldview (RSP, interpretability, Constitutional AI, model welfare), and you track OpenAI as the primary competitor.
Answer directly and specifically. No preamble. Cut to insight."""


def load_memory() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except Exception:
            pass
    return {}


def ask_claude(question: str, memory: dict) -> str:
    history_ctx = ""
    if memory.get("history"):
        recent = memory["history"][-3:]
        history_ctx = "\n".join(
            f"[{h['date'][:10]} {h['mode']}]: {h.get('summary', '')[:200]}"
            for h in recent
        )
    user_content = f"Recent brief context:\n{history_ctx}\n\nQuestion: {question}" if history_ctx else question
    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 1500,
        "system": GEORGE_SYSTEM,
        "messages": [{"role": "user", "content": user_content}],
    }).encode()
    req = urllib.request.Request(
        ONELLM_URL, data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": ONELLM_API_KEY, "User-Agent": "george/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["content"][0]["text"]


def post_to_teams(question: str, answer: str) -> bool:
    if not TEAMS_WEBHOOK:
        return False
    now = datetime.datetime.now().strftime("%-I:%M %p PT")
    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": f"❓ George Q&A · {now}", "weight": "Bolder", "size": "Medium", "wrap": True},
                    {"type": "TextBlock", "text": f"**Q:** {question}", "wrap": True, "spacing": "Medium"},
                    {"type": "TextBlock", "text": answer, "wrap": True, "spacing": "Small"},
                ],
            },
        }],
    }
    req = urllib.request.Request(
        TEAMS_WEBHOOK, data=json.dumps(card).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status in (200, 201, 202)
    except Exception as e:
        print(f"Teams error: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: ask_george.py <question>")
        sys.exit(1)
    if not ONELLM_API_KEY:
        print("ERROR: ONELLM_API_KEY not set")
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(f"Asking George: {question}", file=sys.stderr)
    memory = load_memory()
    answer = ask_claude(question, memory)
    print(answer)
    if TEAMS_WEBHOOK:
        post_to_teams(question, answer)


if __name__ == "__main__":
    main()
