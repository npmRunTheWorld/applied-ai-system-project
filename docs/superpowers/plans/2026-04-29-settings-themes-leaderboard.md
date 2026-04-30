# Settings, Themes & Leaderboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add theme switching, username identity, API key setup help, and a persistent local leaderboard to Glitch Guesser.

**Architecture:** New `leaderboard.py` handles all persistence (JSON file at `data/leaderboard.json`). Theme dicts live at the top of `app.py` and the CSS block is parameterised from the active theme. The game UI is wrapped in `st.tabs` so the Leaderboard tab sits alongside the game.

**Tech Stack:** Python 3.11, Streamlit, pandas (already used), pytest + monkeypatch for leaderboard tests.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `leaderboard.py` | Create | Pure logic: random name, load/save/query JSON leaderboard |
| `tests/test_leaderboard.py` | Create | All leaderboard unit tests |
| `data/.gitkeep` | Create | Ensure `data/` directory tracked |
| `.gitignore` | Modify | Add `data/leaderboard.json` |
| `app.py` | Modify | Theme dicts, parameterised CSS, sidebar (theme + username + API help), tabs, win flow hook |

---

## Task 1: Leaderboard tests (failing)

**Files:**
- Create: `tests/test_leaderboard.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_leaderboard.py
import pytest


def test_generate_random_name_returns_nonempty_string():
    from leaderboard import generate_random_name
    name = generate_random_name()
    assert isinstance(name, str)
    assert len(name) > 0


def test_generate_random_name_has_no_spaces():
    from leaderboard import generate_random_name
    name = generate_random_name()
    assert " " not in name


def test_load_leaderboard_returns_empty_when_no_file(tmp_path, monkeypatch):
    import leaderboard
    monkeypatch.setattr(leaderboard, "LEADERBOARD_FILE", tmp_path / "leaderboard.json")
    assert leaderboard.load_leaderboard() == []


def test_save_score_creates_new_entry(tmp_path, monkeypatch):
    import leaderboard
    monkeypatch.setattr(leaderboard, "DATA_DIR", tmp_path)
    monkeypatch.setattr(leaderboard, "LEADERBOARD_FILE", tmp_path / "leaderboard.json")

    result = leaderboard.save_score("TestPlayer", 150, "Normal", 4)
    assert result is True

    board = leaderboard.load_leaderboard()
    assert len(board) == 1
    assert board[0]["username"] == "TestPlayer"
    assert board[0]["score"] == 150
    assert board[0]["difficulty"] == "Normal"
    assert board[0]["attempts"] == 4


def test_save_score_updates_on_personal_best(tmp_path, monkeypatch):
    import leaderboard
    monkeypatch.setattr(leaderboard, "DATA_DIR", tmp_path)
    monkeypatch.setattr(leaderboard, "LEADERBOARD_FILE", tmp_path / "leaderboard.json")

    leaderboard.save_score("TestPlayer", 100, "Normal", 5)
    result = leaderboard.save_score("TestPlayer", 200, "Hard", 3)
    assert result is True

    board = leaderboard.load_leaderboard()
    assert len(board) == 1          # still one entry per username
    assert board[0]["score"] == 200
    assert board[0]["difficulty"] == "Hard"


def test_save_score_ignores_lower_score(tmp_path, monkeypatch):
    import leaderboard
    monkeypatch.setattr(leaderboard, "DATA_DIR", tmp_path)
    monkeypatch.setattr(leaderboard, "LEADERBOARD_FILE", tmp_path / "leaderboard.json")

    leaderboard.save_score("TestPlayer", 200, "Hard", 3)
    result = leaderboard.save_score("TestPlayer", 100, "Normal", 5)
    assert result is False

    board = leaderboard.load_leaderboard()
    assert board[0]["score"] == 200   # unchanged


def test_get_leaderboard_sorted_descending(tmp_path, monkeypatch):
    import leaderboard
    monkeypatch.setattr(leaderboard, "DATA_DIR", tmp_path)
    monkeypatch.setattr(leaderboard, "LEADERBOARD_FILE", tmp_path / "leaderboard.json")

    leaderboard.save_score("PlayerA", 100, "Easy", 5)
    leaderboard.save_score("PlayerB", 300, "Hard", 2)
    leaderboard.save_score("PlayerC", 200, "Normal", 3)

    board = leaderboard.get_leaderboard()
    assert board[0]["username"] == "PlayerB"
    assert board[1]["username"] == "PlayerC"
    assert board[2]["username"] == "PlayerA"


def test_get_leaderboard_respects_limit(tmp_path, monkeypatch):
    import leaderboard
    monkeypatch.setattr(leaderboard, "DATA_DIR", tmp_path)
    monkeypatch.setattr(leaderboard, "LEADERBOARD_FILE", tmp_path / "leaderboard.json")

    for i in range(15):
        leaderboard.save_score(f"Player{i}", i * 10, "Normal", 5)

    board = leaderboard.get_leaderboard(limit=10)
    assert len(board) == 10
```

- [ ] **Step 2: Run tests — confirm all fail with ImportError**

```bash
pytest tests/test_leaderboard.py -v
```

Expected: All 8 tests FAIL with `ModuleNotFoundError: No module named 'leaderboard'`

---

## Task 2: Implement `leaderboard.py`

**Files:**
- Create: `leaderboard.py`

- [ ] **Step 1: Create `leaderboard.py`**

```python
import json
import time
import random
from pathlib import Path

DATA_DIR = Path("data")
LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"

_ADJECTIVES = [
    "Swift", "Neon", "Cyber", "Glitch", "Dark", "Hyper", "Turbo", "Rogue",
    "Shadow", "Storm", "Void", "Flux", "Nova", "Zero", "Pixel",
]
_NOUNS = [
    "Byte", "Falcon", "Runner", "Ghost", "Blade", "Hawk", "Wolf", "Cipher",
    "Nexus", "Pulse", "Viper", "Comet", "Raven", "Spike", "Drift",
]


def generate_random_name() -> str:
    return random.choice(_ADJECTIVES) + random.choice(_NOUNS)


def load_leaderboard() -> list[dict]:
    if not LEADERBOARD_FILE.exists():
        return []
    with open(LEADERBOARD_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_score(username: str, score: int, difficulty: str, attempts: int) -> bool:
    """Save score only if it beats the player's current best. Returns True if saved."""
    DATA_DIR.mkdir(exist_ok=True)
    board = load_leaderboard()

    existing = next((e for e in board if e["username"] == username), None)
    if existing and existing["score"] >= score:
        return False

    entry = {
        "username": username,
        "score": score,
        "difficulty": difficulty,
        "attempts": attempts,
        "date": time.strftime("%Y-%m-%d"),
    }
    board = [e for e in board if e["username"] != username]
    board.append(entry)

    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2)

    return True


def get_leaderboard(limit: int = 10) -> list[dict]:
    board = load_leaderboard()
    return sorted(board, key=lambda e: e["score"], reverse=True)[:limit]
```

- [ ] **Step 2: Run tests — confirm all pass**

```bash
pytest tests/test_leaderboard.py -v
```

Expected: 8 tests PASS

- [ ] **Step 3: Commit**

```bash
git add leaderboard.py tests/test_leaderboard.py
git commit -m "feat(leaderboard): add leaderboard module with full test coverage"
```

---

## Task 3: Data directory + .gitignore

**Files:**
- Create: `data/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Create data directory**

```bash
mkdir -p data && touch data/.gitkeep
```

- [ ] **Step 2: Add leaderboard.json to .gitignore**

Open `.gitignore` and append:

```
data/leaderboard.json
```

- [ ] **Step 3: Commit**

```bash
git add data/.gitkeep .gitignore
git commit -m "chore: add data dir and gitignore leaderboard.json"
```

---

## Task 4: Theme system in `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add theme dicts at the top of `app.py`, after imports**

Replace the existing `BG_TONES` list and `gv_color` function with:

```python
THEMES = {
    "cyberpunk": {
        "name": "Cyberpunk Neon",
        "bg_tones": ["#05050f", "#030b12", "#05030f", "#0a0318", "#12030a", "#030d10", "#08030f", "#030a0d"],
        "accent":      "#00f5ff",
        "accent2":     "#ff006e",
        "gv_high":     "#39ff14",
        "gv_mid":      "#00f5ff",
        "gv_low":      "#ff4466",
        "text":        "#e0e0ff",
        "muted":       "#8888cc",
        "font_header": "Orbitron",
        "font_body":   "Share Tech Mono",
        "font_import": "https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap",
        "btn_gradient":"linear-gradient(135deg, #ff006e 0%, #00f5ff 100%)",
        "btn_shadow":  "rgba(255,0,110,0.55)",
        "card_bg":     "rgba(0,245,255,0.05)",
        "border":      "rgba(0,245,255,0.35)",
        "chart_score": "#00f5ff",
        "chart_win":   "#39ff14",
        "chart_lose":  "#ff006e",
    },
    "terminal": {
        "name": "Terminal",
        "bg_tones": ["#010a01", "#010801", "#020b02", "#010901", "#010c01", "#020a02", "#010b01", "#020901"],
        "accent":      "#39ff14",
        "accent2":     "#00cc00",
        "gv_high":     "#39ff14",
        "gv_mid":      "#00cc00",
        "gv_low":      "#ff4444",
        "text":        "#c8ffc8",
        "muted":       "#669966",
        "font_header": "Share Tech Mono",
        "font_body":   "Share Tech Mono",
        "font_import": "https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap",
        "btn_gradient":"linear-gradient(135deg, #00cc00 0%, #39ff14 100%)",
        "btn_shadow":  "rgba(57,255,20,0.5)",
        "card_bg":     "rgba(57,255,20,0.05)",
        "border":      "rgba(57,255,20,0.35)",
        "chart_score": "#39ff14",
        "chart_win":   "#00ffcc",
        "chart_lose":  "#ff4444",
    },
    "synthwave": {
        "name": "Synthwave",
        "bg_tones": ["#0d0015", "#0a0012", "#0f0018", "#130010", "#0a001a", "#10000e", "#0d0018", "#0a0010"],
        "accent":      "#ff71ce",
        "accent2":     "#f97316",
        "gv_high":     "#ff71ce",
        "gv_mid":      "#f97316",
        "gv_low":      "#ff4466",
        "text":        "#f0d0ff",
        "muted":       "#aa88cc",
        "font_header": "Audiowide",
        "font_body":   "Rajdhani",
        "font_import": "https://fonts.googleapis.com/css2?family=Audiowide&family=Rajdhani:wght@400;600&display=swap",
        "btn_gradient":"linear-gradient(135deg, #ff71ce 0%, #f97316 100%)",
        "btn_shadow":  "rgba(255,113,206,0.55)",
        "card_bg":     "rgba(255,113,206,0.05)",
        "border":      "rgba(255,113,206,0.35)",
        "chart_score": "#ff71ce",
        "chart_win":   "#7fff7f",
        "chart_lose":  "#f97316",
    },
}


def gv_color(value: int) -> str:
    t = THEMES.get(st.session_state.get("theme", "cyberpunk"), THEMES["cyberpunk"])
    return t["gv_high"] if value > 50 else (t["gv_mid"] if value > 20 else t["gv_low"])
```

- [ ] **Step 2: Add theme selectbox to sidebar (after difficulty section, before the divider that shows Range/Max Attempts)**

Find the sidebar section and add before `st.sidebar.divider()`:

```python
# ── Sidebar ───────────────────────────────────────────────────────────────────
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
attempt_limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
attempt_limit = attempt_limit_map[difficulty]
low, high = get_range_for_difficulty(difficulty)

_theme_names = {k: v["name"] for k, v in THEMES.items()}
_selected_theme_name = st.sidebar.selectbox(
    "Theme",
    options=list(_theme_names.values()),
    index=list(_theme_names.values()).index(
        _theme_names.get(st.session_state.get("theme", "cyberpunk"), "Cyberpunk Neon")
    ),
)
st.session_state.theme = next(k for k, v in THEMES.items() if v["name"] == _selected_theme_name)
```

- [ ] **Step 3: Parameterise the active theme and bg — replace the existing `bg = BG_TONES[...]` line**

```python
# ── Active theme + background cycling ────────────────────────────────────────
t = THEMES.get(st.session_state.get("theme", "cyberpunk"), THEMES["cyberpunk"])
bg = t["bg_tones"][st.session_state.attempts % len(t["bg_tones"])]
```

- [ ] **Step 4: Replace the entire `st.markdown(f""" <style> ... </style> """)` block**

```python
st.markdown(f"""
<style>
  @import url('{t["font_import"]}');

  .stApp {{ background-color: {bg}; transition: background-color 0.8s ease; font-family: '{t["font_body"]}', monospace; }}
  .stApp, .stApp p, .stApp label, .stApp span, .stApp div {{ color: {t["text"]} !important; }}
  .block-container {{ padding-top: 1.2rem; max-width: 860px; }}

  h1 {{
      font-family: '{t["font_header"]}', monospace !important;
      font-size: 1.6rem !important; font-weight: 900; letter-spacing: 0.12em;
      color: {t["accent"]} !important;
      text-shadow: 0 0 18px {t["accent"]}b0, 0 0 40px {t["accent"]}50;
  }}
  h2, h3 {{
      font-family: '{t["font_header"]}', monospace !important;
      color: {t["accent"]} !important; letter-spacing: 0.08em;
  }}

  div[data-testid="stForm"] {{ border: none; padding: 0; }}

  div[data-testid="stTextInput"] input {{
      background: {t["card_bg"]} !important;
      border: 1px solid {t["border"]} !important;
      color: {t["text"]} !important; border-radius: 4px;
      font-family: '{t["font_body"]}', monospace; font-size: 1.1rem;
  }}
  div[data-testid="stTextInput"] input:focus {{
      border-color: {t["accent"]} !important;
      box-shadow: 0 0 14px {t["accent"]}60 !important;
      outline: none !important;
  }}

  div[data-testid="stFormSubmitButton"] button {{
      background: {t["btn_gradient"]};
      color: #fff; font-size: 0.85rem; font-weight: 700;
      letter-spacing: 0.12em; border: none; border-radius: 3px;
      padding: 0.6rem 1.4rem; text-transform: uppercase;
      font-family: '{t["font_header"]}', monospace;
      box-shadow: 0 0 22px {t["btn_shadow"]}, 0 0 44px {t["accent"]}35;
      transition: all 0.2s ease;
  }}
  div[data-testid="stFormSubmitButton"] button:hover {{
      box-shadow: 0 0 34px {t["btn_shadow"]}, 0 0 60px {t["accent"]}60;
      transform: translateY(-1px);
  }}
  div[data-testid="stFormSubmitButton"] button:active {{
      transform: translateY(0); box-shadow: 0 0 12px {t["btn_shadow"]};
  }}

  div[data-testid="stButton"] button {{
      border: 1px solid {t["border"]} !important;
      background: {t["card_bg"]} !important;
      color: {t["accent"]} !important;
      font-family: '{t["font_header"]}', monospace !important;
      font-size: 0.75rem !important; letter-spacing: 0.08em !important;
      border-radius: 3px !important; text-transform: uppercase !important;
      transition: all 0.2s ease !important;
  }}
  div[data-testid="stButton"] button:hover {{
      background: {t["accent"]}25 !important;
      box-shadow: 0 0 14px {t["accent"]}55 !important;
  }}

  div[data-testid="stMetric"] {{
      background: {t["card_bg"]};
      border: 1px solid {t["border"]};
      border-radius: 4px; padding: 8px;
  }}

  section[data-testid="stSidebar"] {{
      background: rgba(3,3,14,0.97) !important;
      border-right: 1px solid {t["border"]};
  }}

  hr {{ border-color: {t["border"]} !important; }}

  .guess-chip {{
      display: inline-block; background: {t["card_bg"]};
      border: 1px solid {t["border"]};
      border-radius: 20px; padding: 1px 10px; margin: 2px;
      font-size: 0.82rem; color: {t["accent"]};
      font-family: '{t["font_body"]}', monospace;
  }}
</style>
""", unsafe_allow_html=True)
```

- [ ] **Step 5: Update JS `gvColor` to use theme accent colors from the injected `t` dict**

In the `components.html(f"""...""")` block, replace:

```javascript
  function gvColor(v) {{
    return v > 50 ? '#39ff14' : v > 20 ? '#00f5ff' : '#ff4466';
  }}
```

with:

```javascript
  const GV_HIGH = '{t["gv_high"]}';
  const GV_MID  = '{t["gv_mid"]}';
  const GV_LOW  = '{t["gv_low"]}';
  function gvColor(v) {{
    return v > 50 ? GV_HIGH : v > 20 ? GV_MID : GV_LOW;
  }}
```

- [ ] **Step 6: Update all inline style color references to use `t` dict**

Find and replace these hardcoded values throughout `app.py`:

| Find | Replace with |
|------|-------------|
| `color:#9e9e9e` | `color:{t["muted"]}` |
| `color:#8888cc` | `color:{t["muted"]}` |
| `color:#fafafa` | `color:{t["accent"]}` |
| `color:#00f5ff` | `color:{t["accent"]}` |
| `color:#aaa` | `color:{t["muted"]}` |
| `background:rgba(0,245,255,0.05)` | `background:{t["card_bg"]}` |
| `border:1px solid rgba(0,245,255,0.2)` | `border:1px solid {t["border"]}` |
| `color:#748FFC` (coach suggestion number) | `color:{t["accent"]}` |
| `background:rgba(255,0,110,0.07);border:1px solid rgba(255,0,110,0.35)` (coach box) | `background:{t["card_bg"]};border:1px solid {t["border"]}` |
| `color:#39ff14` (conf high) | `color:{t["gv_high"]}` |
| `color:#00f5ff` (conf mid) | `color:{t["accent"]}` |
| `color:#ff4466` (conf low) | `color:{t["gv_low"]}` |

Also update chart color scale (already using variables from task above) — the chart `color_scale` domain values should use `t`:

```python
color_scale = alt.Scale(
    domain=["Score", "Win ▲", "Lose ▼"],
    range=[t["chart_score"], t["chart_win"], t["chart_lose"]],
)
```

And chart axis `labelColor` and `gridColor`:

```python
x=alt.X("attempt:Q", title=None, axis=alt.Axis(tickMinStep=1, labelColor=t["muted"], gridColor=t["border"])),
y=alt.Y("score:Q", title=None,
        scale=alt.Scale(domain=[0, max(130, current_score + gv_now + 20)]),
        axis=alt.Axis(labelColor=t["muted"], gridColor=t["border"])),
color=alt.Color("series:N", scale=color_scale,
                legend=alt.Legend(title=None, labelColor=t["text"])),
```

And the Lose ▼ label color:

```python
+ _make_label_chart(n + 1, lose_score, f"{lose_score} pts", t["chart_lose"], dy=8)
```

And CHIP_COLORS in history:

```python
CHIP_COLORS = {
    "Too Low":  (f"rgba(255,0,110,0.18)",   t["accent2"]),
    "Too High": (t["card_bg"],              t["accent"]),
    "Win":      (f"rgba(57,255,20,0.15)",   t["gv_high"]),
}
```

And the history legend badges:

```python
st.markdown(
    f'<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;">'
    f'<span style="font-size:0.7rem;background:rgba(255,0,110,0.15);color:{t["accent2"]};'
    f'border:1px solid {t["accent2"]}66;border-radius:3px;padding:2px 8px;letter-spacing:0.06em;">▼ TOO LOW</span>'
    f'<span style="font-size:0.7rem;background:{t["card_bg"]};color:{t["accent"]};'
    f'border:1px solid {t["border"]};border-radius:3px;padding:2px 8px;letter-spacing:0.06em;">▲ TOO HIGH</span>'
    f'<span style="font-size:0.7rem;background:rgba(57,255,20,0.1);color:{t["gv_high"]};'
    f'border:1px solid {t["gv_high"]}66;border-radius:3px;padding:2px 8px;letter-spacing:0.06em;">✓ CORRECT</span>'
    f'</div>',
    unsafe_allow_html=True,
)
```

- [ ] **Step 7: Run the app and manually verify theme switching works**

```bash
python3 -m streamlit run app.py
```

Switch between Cyberpunk Neon / Terminal / Synthwave in sidebar. Confirm colors, fonts, and chart update.

- [ ] **Step 8: Commit**

```bash
git add app.py
git commit -m "feat(themes): add theme system with Cyberpunk, Terminal, Synthwave"
```

---

## Task 5: Username sidebar + API key help

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add leaderboard import at the top of `app.py` (after existing imports)**

```python
import leaderboard as lb
```

- [ ] **Step 2: Add username to session state defaults**

In the `defaults` dict, add two new keys:

```python
defaults = {
    "secret": random.randint(low, high),
    "attempts": 0, "score": 100, "status": "playing",
    "history": [], "history_outcomes": [], "game_id": 0, "last_hint": None,
    "start_time": time.time(), "score_delta": None,
    "score_history": [100],
    "username": lb.generate_random_name(),
    "username_locked": False,
}
```

- [ ] **Step 3: Add username section to sidebar — place it between the Range/Attempts divider and the existing API key divider**

Find:
```python
st.sidebar.divider()
_user_key = st.sidebar.text_input(
```

Insert before it:

```python
st.sidebar.divider()
st.sidebar.markdown("**Player**")
if st.session_state.username_locked:
    st.sidebar.markdown(f"**{st.session_state.username}**")
    st.sidebar.caption("Locked after first win")
else:
    _new_name = st.sidebar.text_input(
        "Username",
        value=st.session_state.username,
        max_chars=20,
        help="Set your name before your first win — it locks in after that.",
    )
    if _new_name and _new_name != st.session_state.username:
        st.session_state.username = _new_name

st.sidebar.divider()
_user_key = st.sidebar.text_input(
```

- [ ] **Step 4: Add API key help expander — place it directly after the `_user_key` text_input**

Find:
```python
    key="user_api_key",
)
```

Add after it:

```python
with st.sidebar.expander("How to get an API key"):
    st.markdown(
        "1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in\n"
        "2. Navigate to **API Keys** → **Create Key**\n"
        "3. Copy the key and paste it above"
    )
```

- [ ] **Step 5: Run the app and confirm username shows in sidebar, locks are absent, help expander works**

```bash
python3 -m streamlit run app.py
```

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat(settings): username sidebar with random default + API key help"
```

---

## Task 6: Wrap game in tabs + leaderboard UI

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Wrap the main body content in tabs**

Find the header line:
```python
st.title("🎮 Glitch Guesser")
```

Before it, add:
```python
tab_game, tab_board = st.tabs(["🎮 Game", "🏆 Leaderboard"])
```

Then indent all game content (from `st.title(...)` through the last `with bot_right:` block) inside `with tab_game:`. The structure becomes:

```python
tab_game, tab_board = st.tabs(["🎮 Game", "🏆 Leaderboard"])

with tab_game:
    st.title("🎮 Glitch Guesser")
    # ... all existing game content ...

with tab_board:
    # Task 6 Step 2 goes here
```

- [ ] **Step 2: Add leaderboard content inside `with tab_board:`**

```python
with tab_board:
    st.markdown(f"### 🏆 Top Players")
    board = lb.get_leaderboard(limit=10)
    current_user = st.session_state.get("username", "")

    if not board:
        st.caption("No scores yet — win a game to get on the board!")
    else:
        rows = []
        for i, entry in enumerate(board):
            rows.append({
                "Rank":       f"▶ #{i+1}" if entry["username"] == current_user else f"#{i+1}",
                "Player":     entry["username"],
                "Score":      entry["score"],
                "Difficulty": entry["difficulty"],
                "Attempts":   entry["attempts"],
                "Date":       entry["date"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Showing top {len(board)} scores. Your row is marked ▶.")
```

- [ ] **Step 3: Run the app and verify both tabs work, leaderboard shows "No scores yet"**

```bash
python3 -m streamlit run app.py
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat(leaderboard): add tabs layout and leaderboard display"
```

---

## Task 7: Wire win flow to leaderboard save

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Find the win branch inside the submit handler and add leaderboard save + lock**

Find:
```python
                if outcome == "Win":
                    gv = guess_volatility(
                        st.session_state.attempts, attempt_limit,
                        int(time.time() - st.session_state.start_time)
                    )
                    st.session_state.score = update_score(prev, outcome, penalty) + gv
                    st.session_state.score_delta = gv if gv > 0 else None
                    st.balloons()
                    st.session_state.status = "won"
```

Replace with:
```python
                if outcome == "Win":
                    gv = guess_volatility(
                        st.session_state.attempts, attempt_limit,
                        int(time.time() - st.session_state.start_time)
                    )
                    st.session_state.score = update_score(prev, outcome, penalty) + gv
                    st.session_state.score_delta = gv if gv > 0 else None
                    st.balloons()
                    st.session_state.status = "won"
                    st.session_state.username_locked = True
                    is_best = lb.save_score(
                        st.session_state.username,
                        st.session_state.score,
                        difficulty,
                        st.session_state.attempts,
                    )
                    st.session_state["_new_personal_best"] = is_best
```

- [ ] **Step 2: Show the personal best banner in the win/loss banner section**

Find:
```python
if st.session_state.status == "won":
    st.success(f"🏆 Won! Secret: **{st.session_state.secret}** · {elapsed}s · Score: **{st.session_state.score}**")
```

Replace with:
```python
if st.session_state.status == "won":
    st.success(f"🏆 Won! Secret: **{st.session_state.secret}** · {elapsed}s · Score: **{st.session_state.score}**")
    if st.session_state.pop("_new_personal_best", False):
        st.success("🌟 New personal best — score saved to leaderboard!")
```

- [ ] **Step 3: Run the app, play a game, win, and verify**

```bash
python3 -m streamlit run app.py
```

Checklist:
- Win banner shows
- "New personal best" banner shows on first win
- Username is locked in sidebar after winning
- Switch to Leaderboard tab — player's score appears with ▶ marker
- Win again with higher score — "New personal best" shows and leaderboard updates
- Win again with lower score — no personal best banner, leaderboard unchanged

- [ ] **Step 4: Run full test suite**

```bash
pytest -v
```

Expected: All tests pass (including the 8 leaderboard tests)

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(leaderboard): wire win flow to save scores and lock username"
```

---

## Done

All features implemented:
- ✅ API key help expander in sidebar
- ✅ Theme switcher (Cyberpunk / Terminal / Synthwave) in sidebar
- ✅ Random username, set once, locked on first win
- ✅ Leaderboard tab with top 10, personal best highlighted
- ✅ Score auto-saved on win, personal best banner shown
