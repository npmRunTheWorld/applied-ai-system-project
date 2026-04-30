# Session Notes

## Last Updated: 2026-04-30

---

## What We Accomplished

### Session 5 — arch-01 continuation

**Theme System**
- 3 selectable themes: Cyberpunk Neon, Terminal, Synthwave
- Full CSS parameterisation via `THEMES` dict — fonts, colors, gradients, chart palette, chip colors all theme-driven
- `_hex_rgba()` helper converts hex theme colors to rgba backgrounds
- JS `gvColor` uses injected theme constants

**Leaderboard (`leaderboard.py`)**
- Persistent `data/leaderboard.json` — one personal-best entry per username
- `generate_random_name()` — adjective+noun combos (225 combinations)
- `save_score()` — only saves if new personal best, returns bool
- `get_leaderboard(limit=10)` — sorted descending by score
- 8 unit tests, all passing

**Settings / Sidebar**
- Username: random default, editable once, locked permanently after first win
- API key: password-masked input + collapsible "How to get an API key" help expander
- Theme selectbox in sidebar

**Leaderboard UI**
- Game / Leaderboard tabs (`st.tabs`)
- Top 10 table, current player's row marked with ▶
- Personal best banner on win

**AI Coach updates**
- Per-call API key support (user-supplied key takes priority over env var)
- Model downgraded `claude-opus-4-7` → `claude-sonnet-4-6` for cost savings
- Billing errors now surface actionable message instead of generic "API error"

**Bug Fixes**
- `username_locked` AttributeError on startup — early session state init before sidebar
- Difficulty switch kept stale secret from previous difficulty — detect change, clear game state

**Docs & Submission**
- `reflection.md` — all 5 questions completed
- `architecture.mmd` — Mermaid diagram of full system
- Loom walkthrough recorded and linked in README

---

## Files Targeted This Session

| File | Change |
|------|--------|
| `app.py` | Themes, sidebar, tabs, leaderboard UI, win flow, difficulty reset fix |
| `ai_coach.py` | Per-call API key, model downgrade, better error messages |
| `leaderboard.py` | New — full persistence module |
| `tests/test_leaderboard.py` | New — 8 tests |
| `data/.gitkeep` | New |
| `architecture.mmd` | New — Mermaid diagram |
| `requirements.txt` | Added python-dotenv |
| `reflection.md` | Completed all 5 questions |
| `.gitignore` | Added data/leaderboard.json |
| `docs/` | Design spec + implementation plan |

---

## What's In Progress

- PR #1 open: `feature/arch-01` → `main`
- Loom video linked in README

## Next Steps

- Merge PR #1 to complete assignment submission
- Consider cloud persistence if app is hosted publicly
