#!/usr/bin/env python3
"""
George — AI Intelligence System
Twice-daily AI frontier brief (Anthropic-first, plus OpenAI) for Theodore Simmons.
Brain: Claude Opus 4.6 via ServiceNow OneLLM proxy
Source of truth: TheoOS repo, george/ (~/george is a symlink to it)
Secrets: ~/.george/.env (see .env.example)
"""

import os
import sys
import json
import re
import hashlib
import datetime
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, List

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


# ── CONFIG ────────────────────────────────────────────────────────────────────

ONELLM_API_KEY = os.environ.get("ONELLM_API_KEY", "")
TEAMS_WEBHOOK = os.environ.get("TEAMS_WEBHOOK", "")
EMAIL_WEBHOOK = os.environ.get("EMAIL_WEBHOOK", "")
ONELLM_URL = "https://apicid-dev.servicenow.com/v4/onellm/models/anthropic?model=claude-opus-4-6"
MEMORY_FILE = Path.home() / ".george" / "memory.json"

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── MEMORY ────────────────────────────────────────────────────────────────────

def load_memory() -> Dict:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except Exception as e:
            print(f"Memory load error: {e}", file=sys.stderr)
    return {
        "last_run": None,
        "last_morning": None,
        "history": [],
        "seen_hashes": [],
        "trends": {},
    }


def save_memory(memory: Dict) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat()
    memory["history"] = [h for h in memory.get("history", []) if h.get("date", "") >= cutoff]
    memory["seen_hashes"] = memory.get("seen_hashes", [])[-2000:]
    MEMORY_FILE.write_text(json.dumps(memory, indent=2, default=str))


# ── FETCHING ──────────────────────────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers=FETCH_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FETCH WARN {url[:70]}: {e}", file=sys.stderr)
        return None


def parse_feed(xml_text: str, max_items: int = 10, source_name: str = "") -> List[Dict]:
    """Parse RSS or Atom feed into list of dicts."""
    items = []
    try:
        xml_clean = re.sub(r'\sxmlns(?::\w+)?="[^"]+"', '', xml_text)
        xml_clean = re.sub(r'<(/?)[\w]+:', r'<\1', xml_clean)
        root = ET.fromstring(xml_clean)

        entries = root.findall(".//entry")
        if entries:
            for e in entries[:max_items]:
                title = re.sub(r'<!\[CDATA\[|\]\]>', '', e.findtext("title") or "").strip()
                link_el = e.find("link")
                link = (link_el.get("href", "") if link_el is not None else "") or (e.findtext("link") or "")
                summary = ""
                for tag in ["summary", "content", "description"]:
                    val = e.findtext(tag)
                    if val:
                        summary = re.sub(r'<[^>]+>', ' ', val).strip()[:500]
                        break
                published = (e.findtext("published") or e.findtext("updated") or "").strip()
                if title:
                    items.append({"title": title, "link": link, "summary": summary, "published": published, "source": source_name})
        else:
            for item in root.findall(".//item")[:max_items]:
                title = re.sub(r'<!\[CDATA\[|\]\]>', '', item.findtext("title") or "").strip()
                link = (item.findtext("link") or item.findtext("guid") or "").strip()
                summary = ""
                for tag in ["description", "summary"]:
                    val = item.findtext(tag)
                    if val:
                        summary = re.sub(r'<[^>]+>', ' ', val).strip()[:500]
                        break
                published = (item.findtext("pubDate") or "").strip()
                if title:
                    items.append({"title": title, "link": link, "summary": summary, "published": published, "source": source_name})
    except Exception as e:
        print(f"  PARSE WARN ({source_name}): {e}", file=sys.stderr)
    return items


def scrape_anthropic_blog(max_articles: int = 6) -> List[Dict]:
    """Scrape Anthropic news page (no public RSS)."""
    html = fetch_url("https://www.anthropic.com/news")
    if not html:
        return []
    items = []
    paths = list(dict.fromkeys(re.findall(r'href="(/news/[^"#?]+)"', html)))
    for path in paths:
        if path in ("/news",) or path.startswith("/news?"):
            continue
        url = f"https://www.anthropic.com{path}"
        page = fetch_url(url, timeout=10)
        if not page:
            continue
        title = ""
        m = re.search(r'<title[^>]*>([^<]+)</title>', page)
        if m:
            title = re.sub(r'\s*[\|—]\s*Anthropic\s*$', '', m.group(1).strip(), flags=re.I).strip()
        if not title:
            continue
        summary = ""
        for pattern in [
            r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"',
            r'<meta[^>]+content="([^"]+)"[^>]+property="og:description"',
            r'<meta[^>]+name="description"[^>]+content="([^"]+)"',
        ]:
            m = re.search(pattern, page)
            if m:
                summary = m.group(1).strip()
                break
        published = ""
        m = re.search(r'/news/(\d{4}-\d{2}-\d{2})', path)
        if m:
            published = m.group(1)
        items.append({"title": title, "link": url, "summary": summary[:500], "published": published, "source": "anthropic_blog"})
        if len(items) >= max_articles:
            break
    return items


def item_hash(item: Dict) -> str:
    key = (item.get("title", "") + item.get("link", "")).lower().strip()
    return hashlib.md5(key.encode()).hexdigest()[:12]


def filter_new(items: List[Dict], memory: Dict) -> List[Dict]:
    seen = set(memory.get("seen_hashes", []))
    return [item for item in items if item_hash(item) not in seen]


def collect_all_sources() -> Dict[str, List[Dict]]:
    """Fetch all configured sources."""
    print("Collecting sources...", file=sys.stderr)
    data: Dict[str, List[Dict]] = {
        "anthropic": [], "claude_code": [], "openai": [], "research": [], "competition": [], "people": []
    }

    print("  Anthropic blog...", file=sys.stderr)
    data["anthropic"] += scrape_anthropic_blog()

    print("  Claude Code releases...", file=sys.stderr)
    t = fetch_url("https://github.com/anthropics/claude-code/releases.atom")
    if t:
        data["claude_code"] += parse_feed(t, max_items=5, source_name="claude_code")

    t = fetch_url("https://github.com/anthropics/anthropic-sdk-python/releases.atom")
    if t:
        data["anthropic"] += parse_feed(t, max_items=3, source_name="anthropic_sdk")

    print("  ArXiv cs.AI+cs.LG...", file=sys.stderr)
    t = fetch_url("https://rss.arxiv.org/rss/cs.AI+cs.LG")
    if t:
        data["research"] += parse_feed(t, max_items=20, source_name="arxiv")

    print("  OpenAI news + Codex/SDK releases...", file=sys.stderr)
    for url in ["https://openai.com/news/rss.xml", "https://openai.com/blog/rss.xml"]:
        t = fetch_url(url)
        if t and ("<item" in t or "<entry" in t):
            data["openai"] += parse_feed(t, max_items=6, source_name="openai")
            break

    t = fetch_url("https://github.com/openai/codex/releases.atom")
    if t:
        data["openai"] += parse_feed(t, max_items=4, source_name="openai_codex")

    t = fetch_url("https://github.com/openai/openai-python/releases.atom")
    if t:
        data["openai"] += parse_feed(t, max_items=3, source_name="openai_sdk")

    print("  DeepMind blog...", file=sys.stderr)
    for deepmind_url in ["https://deepmind.google/blog/rss.xml", "https://deepmind.google/discover/blog/rss.xml"]:
        t = fetch_url(deepmind_url)
        if t and ("<item" in t or "<entry" in t):
            data["competition"] += parse_feed(t, max_items=5, source_name="deepmind")
            break

    for meta_url in ["https://engineering.fb.com/feed/", "https://ai.meta.com/blog/rss/"]:
        t = fetch_url(meta_url)
        if t and ("<item" in t or "<entry" in t):
            data["competition"] += parse_feed(t, max_items=5, source_name="meta_ai")
            break

    print("  Google News...", file=sys.stderr)
    gnews_queries = [
        ("Dario+Amodei", "people"),
        ("Daniela+Amodei", "people"),
        ("Amanda+Askell+AI", "people"),
        ("Chris+Olah+AI+interpretability", "people"),
        ("Sam+Altman+OpenAI", "openai"),
        ("OpenAI+announcement", "openai"),
        ("ChatGPT+Codex+OpenAI", "openai"),
        ("Anthropic+AI+announcement", "anthropic"),
        ("Claude+AI+Anthropic", "anthropic"),
        ("AI+safety+alignment+research", "research"),
    ]
    for query, cat in gnews_queries:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        t = fetch_url(url)
        if t:
            data[cat] += parse_feed(t, max_items=3, source_name=f"gnews_{query[:20]}")

    return data


# ── CLAUDE VIA ONELLM ─────────────────────────────────────────────────────────

def ask_claude(messages: List[Dict], system: str = "", max_tokens: int = 2000) -> Optional[str]:
    if not ONELLM_API_KEY:
        print("ERROR: ONELLM_API_KEY not set. Must be on ServiceNow VPN.", file=sys.stderr)
        return None
    payload = {
        "model": "claude-opus-4-6",
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ONELLM_URL,
        data=body,
        headers={"Content-Type": "application/json", "X-API-Key": ONELLM_API_KEY, "User-Agent": "george/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]
    except Exception as e:
        print(f"ERROR calling Claude: {e}", file=sys.stderr)
        return None


# ── PROMPT TEMPLATES ──────────────────────────────────────────────────────────

GEORGE_SYSTEM = """You are George — Theodore Simmons' personal AI intelligence analyst. Theodore is a senior AI strategist at ServiceNow working at the intersection of AI capabilities and enterprise software. He has deep Anthropic knowledge and uses Claude Code daily.

You reason from Anthropic's actual worldview:
- **RSP**: ASL-2/3/4 thresholds. If ASL-3 signals appear, treat it as the single biggest story in AI.
- **Interpretability**: Chris Olah's circuits/superposition work. Breakthroughs here change everything.
- **Constitutional AI**: Claude's values are trained, not guardrails. When other labs adopt it, Anthropic's thesis is validated.
- **Model welfare**: Anthropic genuinely researches whether Claude has morally relevant states.
- **Core bet**: Safety and capability are the same thing done right.
- **Claude's character**: Real values, not filters.

OpenAI is the primary competitor. Read its releases against Anthropic's positioning: Codex vs Claude Code, enterprise/agent moves, and safety posture (Preparedness Framework vs RSP). Report what actually shipped, not marketing.

Write like you're briefing a smart, busy founder who already read the news. No preamble. Cut to signal. Every word earns its place.

Signal tiers:
- ⚡ **ACT**: Something changed that requires action TODAY
- 👁️ **WATCH**: Real signal, track closely, don't act yet
- 😴 **QUIET**: Nothing materially new

Format in clean Markdown suitable for Teams. Bold for emphasis, bullets for lists. Keep sections tight."""


def format_sources_for_prompt(new_sources: Dict[str, List[Dict]], mode: str, memory: Dict) -> str:
    parts = []
    for category, items in new_sources.items():
        if not items:
            continue
        parts.append(f"\n## {category.upper()} ({len(items)} new items)")
        for item in items[:15]:
            parts.append(f"- **{item['title']}**")
            if item.get("summary"):
                parts.append(f"  {item['summary'][:200]}")
            if item.get("link"):
                parts.append(f"  {item['link']}")

    if memory.get("trends"):
        parts.append("\n## RECENT TRENDS (from memory)")
        for trend, count in sorted(memory["trends"].items(), key=lambda x: -x[1])[:10]:
            parts.append(f"- {trend}: seen {count}x recently")

    if mode == "evening" and memory.get("history"):
        last = [h for h in memory["history"] if h.get("mode") == "morning"]
        if last:
            parts.append(f"\n## THIS MORNING'S BRIEF (context)\n{last[-1].get('summary', '')[:500]}")

    return "\n".join(parts) if parts else "No new items found across all sources."


def generate_morning_brief(sources_text: str) -> Optional[str]:
    prompt = f"""Here's what happened in AI since the last brief:

{sources_text}

Generate George's morning brief. Include ALL sections:

**🧠 Anthropic This Week**
Model releases, SDK updates, leader signals, blog posts. Interpret through Anthropic's actual worldview. If nothing new, one line.

**🛠️ Claude Code Update**
New releases or changes. Translate to: "here's what Theodore should actually do with this today." If nothing new, one line.

**🟢 OpenAI This Week**
Model releases, Codex and SDK updates, leader signals (Altman et al.), blog posts. State what shipped and how it lands against Anthropic. If nothing new, one line.

**📰 Research Worth Knowing**
2-3 ArXiv papers that matter for applied AI or ServiceNow. One sentence each: what it found + why it matters to Theodore specifically.

**🏢 What the Competition Shipped**
Google, Meta, and anyone else notable (OpenAI has its own section). Skip marketing announcements. Only what actually shipped.

**📈 Trend Watch**
Patterns emerging across the last few days. 2-3 bullets max.

**⚡ George's Take**
Signal tier: QUIET / WATCH / ACT — then one sharp paragraph on what this means for Theodore's work at ServiceNow. No hedging.

**✅ Do This Today**
2-4 specific, actionable items with exact commands where relevant. Based on what actually changed.

Write tight. No filler."""

    return ask_claude([{"role": "user", "content": prompt}], system=GEORGE_SYSTEM, max_tokens=3200)


def generate_evening_brief(sources_text: str) -> Optional[str]:
    prompt = f"""What happened in AI since the morning brief (approx 8:30am PT):

{sources_text}

Generate George's evening delta brief.
- Only include signals that appeared SINCE this morning (Anthropic and OpenAI both count)
- Skip anything covered this morning
- If nothing meaningful happened: respond with exactly "SKIP" and nothing else
- If there IS new signal:

**🌆 Evening Delta**
What changed since this morning.

**⚡ Signal**: QUIET / WATCH / ACT + one sentence on what it means.

Keep it very short — this is an update, not a full brief."""

    return ask_claude([{"role": "user", "content": prompt}], system=GEORGE_SYSTEM, max_tokens=800)


# ── TEAMS DELIVERY ────────────────────────────────────────────────────────────

def post_to_teams(content: str, mode: str) -> bool:
    if not TEAMS_WEBHOOK:
        print("ERROR: TEAMS_WEBHOOK not set", file=sys.stderr)
        return False
    now = datetime.datetime.now().strftime("%A, %B %-d at %-I:%M %p PT")
    mode_label = "☀️ Morning Brief" if mode == "morning" else "🌙 Evening Update"
    title = f"George — {mode_label} · {now}"
    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Large", "wrap": True},
                    {"type": "TextBlock", "text": content, "wrap": True, "spacing": "Medium"},
                ],
            },
        }],
    }
    payload = json.dumps(card).encode("utf-8")
    req = urllib.request.Request(
        TEAMS_WEBHOOK, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")[:100]
            print(f"Teams response: {status} {body}", file=sys.stderr)
            return status in (200, 201, 202)
    except Exception as e:
        print(f"ERROR posting to Teams: {e}", file=sys.stderr)
        return False


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="George AI Intelligence System")
    parser.add_argument("--mode", choices=["morning", "evening"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="Print brief, don't post to Teams")
    args = parser.parse_args()
    mode = args.mode

    print(f"George starting — mode: {mode} — {datetime.datetime.now().isoformat()}", file=sys.stderr)

    if not ONELLM_API_KEY:
        print("FATAL: ONELLM_API_KEY not set. Must be on ServiceNow VPN.", file=sys.stderr)
        sys.exit(1)

    memory = load_memory()

    all_sources = collect_all_sources()

    new_sources: Dict[str, List[Dict]] = {}
    total_new = 0
    for cat, items in all_sources.items():
        new_items = filter_new(items, memory)
        new_sources[cat] = new_items
        total_new += len(new_items)
    print(f"Found {total_new} new items", file=sys.stderr)

    sources_text = format_sources_for_prompt(new_sources, mode, memory)

    print(f"Generating {mode} brief via Claude Opus...", file=sys.stderr)
    if mode == "morning":
        brief = generate_morning_brief(sources_text)
    else:
        brief = generate_evening_brief(sources_text)

    if not brief:
        print("ERROR: Failed to generate brief", file=sys.stderr)
        sys.exit(1)

    if mode == "evening" and brief.strip().upper() == "SKIP":
        print("Evening brief: nothing meaningful — skipping Teams post.", file=sys.stderr)
        memory["last_run"] = datetime.datetime.utcnow().isoformat()
        save_memory(memory)
        return

    print("\n" + "=" * 60, file=sys.stderr)
    print(brief[:600], file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if args.dry_run:
        print("\n--- DRY RUN ---")
        print(brief)
    else:
        success = post_to_teams(brief, mode)
        if success:
            print("Successfully posted to Teams", file=sys.stderr)
        else:
            print("WARNING: Failed to post to Teams", file=sys.stderr)

    # Update memory
    mark_seen = lambda items: None  # inline below
    seen_set = set(memory.get("seen_hashes", []))
    for cat_items in new_sources.values():
        for item in cat_items:
            seen_set.add(item_hash(item))
    memory["seen_hashes"] = list(seen_set)

    memory["last_run"] = datetime.datetime.utcnow().isoformat()
    if mode == "morning":
        memory["last_morning"] = datetime.datetime.utcnow().isoformat()

    memory.setdefault("history", []).append({
        "date": datetime.datetime.utcnow().isoformat(),
        "mode": mode,
        "summary": brief[:500],
        "items_seen": total_new,
    })

    trends = memory.get("trends", {})
    key_terms = re.compile(
        r'\b(GPT|Codex|ChatGPT|Claude|Gemini|Llama|OpenAI|Anthropic|DeepMind|ASL|interpretability|'
        r'safety|alignment|reasoning|agent|multimodal|benchmark|RLHF|Constitutional|RSP)\b',
        re.I,
    )
    for cat_items in new_sources.values():
        for item in cat_items:
            for word in key_terms.findall(item.get("title", "")):
                k = word.lower()
                trends[k] = trends.get(k, 0) + 1
    memory["trends"] = trends

    save_memory(memory)
    print("Memory saved.", file=sys.stderr)


if __name__ == "__main__":
    main()
