# George — AI Intelligence System

Twice-daily AI frontier brief (Anthropic-first, plus OpenAI) posted to Teams. Brain: Claude Opus via the ServiceNow OneLLM proxy (VPN only).

- `george.py --mode morning|evening [--dry-run]` — collect sources, brief, post Adaptive Card to Teams
- `ask_george.py "question"` — ad-hoc Q&A (alias `george`)
- Secrets: copy `.env.example` to `~/.george/.env` (chmod 600). Never commit it.
- Scheduling: launchd agents `com.george.{morningbrief,eveningbrief}` run `~/george/george.py` (symlink to this directory), weekdays 8:30 PT.
- Memory: `~/.george/memory.json` (30-day rolling). Note `--dry-run` still writes it.
- Sources: Anthropic news, Claude Code/SDK releases, OpenAI news + Codex/SDK releases, ArXiv, DeepMind/Meta, Google News on leaders.
