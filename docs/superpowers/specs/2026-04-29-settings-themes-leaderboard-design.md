# Settings, Themes & Leaderboard Design
**Date:** 2026-04-29  
**Branch:** feature/arch-01  
**Status:** Approved

---

## Overview

Three connected features added to Glitch Guesser:

1. **API Key Help** — inline instructions for getting an Anthropic key
2. **Theme System** — three selectable visual themes via sidebar
3. **Leaderboard** — persistent per-player high scores with username identity

---

## 1. API Key Help

**Location:** Sidebar, directly under the existing API key `text_input`.

**Implementation:** `st.expander("How to get an API key")` with three steps:
1. Go to `console.anthropic.com` → sign up / log in
2. Navigate to API Keys → Create Key
3. Copy and paste it into the field above

No new files. No state changes.

---

## 2. Theme System

### Themes

| Name | BG | Primary Accent | Secondary Accent | Font (header) | Font (body) |
|------|----|---------------|-----------------|---------------|-------------|
| Cyberpunk Neon | `#05050f` cycling | `#00f5ff` cyan | `#ff006e` magenta | Orbitron | Share Tech Mono |
| Terminal | `#010a01` cycling | `#39ff14` green | `#00cc00` mid-green | Share Tech Mono | Share Tech Mono |
| Synthwave | `#0d0015` cycling | `#ff71ce` pink | `#f97316` orange | Audiowide | Rajdhani |

### State

- `st.session_state.theme` — string key (`"cyberpunk"` / `"terminal"` / `"synthwave"`), default `"cyberpunk"`
- Sidebar `st.selectbox("Theme", ...)` writes to session state on change

### Implementation

- Theme dicts defined at top of `app.py` (colors, fonts, BG tones)
- Existing CSS `st.markdown` block parameterised from active theme dict
- `BG_TONES` and `gv_color` thresholds remain unchanged; accent colors swap per theme
- JS `gvColor` function updated: theme accent hex values passed as JS string literals inside the `components.html` f-string block

### No new files — all changes in `app.py`.

---

## 3. Leaderboard

### New file: `leaderboard.py`

**Functions:**

```
generate_random_name() -> str
    Returns e.g. "SwiftByte", "NeonFalcon" — adjective + noun combo.
    Called once on first session load if no username set.

load_leaderboard() -> list[dict]
    Reads data/leaderboard.json. Returns [] if file missing.
    Each entry: { username, score, difficulty, attempts, date }

save_score(username: str, score: int, difficulty: str, attempts: int) -> bool
    Saves only if score > player's existing best (or player is new).
    Returns True if it was a new personal best.

get_leaderboard(limit: int = 10) -> list[dict]
    Returns top-N entries sorted by score descending.
```

### Storage

- `data/leaderboard.json` — array of objects, one entry per unique username (personal best only)
- Created automatically on first save
- Gitignored (player data should not be committed)

### Username Flow

1. On first load, `generate_random_name()` is called and stored in `st.session_state.username`
2. Sidebar shows a text input pre-filled with the random name
3. After the user's first win, `st.session_state.username_locked = True` — win is the lock trigger
4. Once locked, the input is replaced with a static display of the name — no further edits

### Win Flow

1. Player wins → existing win banner fires
2. `save_score()` called automatically
3. If returns `True` (new personal best) → additional `st.success("🏆 New personal best!")` banner
4. Score appears/updates on leaderboard immediately

### Leaderboard UI

- Implemented as a **Streamlit tab** (`st.tabs(["Game", "Leaderboard"])`) wrapping the main game content
- Leaderboard tab shows:
  - Top 10 players, sorted by score descending
  - Columns: Rank | Username | Score | Difficulty | Attempts | Date
  - Current player's row highlighted with cyan background
  - "No scores yet" placeholder when empty

### New files

- `leaderboard.py` — pure logic, no Streamlit imports
- `data/.gitkeep` — ensures `data/` directory is tracked

### Changes to `app.py`

- Import `leaderboard` module
- Wrap layout in `st.tabs(["🎮 Game", "🏆 Leaderboard"])`
- Add username sidebar section (above API key section)
- Add theme selectbox to sidebar
- Call `leaderboard.save_score()` in win branch
- Render leaderboard table in Leaderboard tab

---

## File Change Summary

| File | Change |
|------|--------|
| `app.py` | Theme system, username sidebar, tabs, win flow hook |
| `leaderboard.py` | New — all leaderboard logic |
| `data/.gitkeep` | New — ensures data dir exists |
| `.gitignore` | Add `data/leaderboard.json` |

---

## Out of Scope

- Cross-device / cloud leaderboard (future: swap `leaderboard.py` backend)
- Authentication
- Score verification / anti-cheat
