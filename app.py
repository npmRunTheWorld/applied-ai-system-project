import json
import random
import time
import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components
from logic_utils import (
    get_range_for_difficulty,
    parse_guess,
    check_guess,
    update_score,
    guess_volatility,
)
from ai_coach import get_coach_hint
import leaderboard as lb

HINT_MESSAGES = {
    "Too High": ("📉 Too High — Go Lower", "warning"),
    "Too Low":  ("📈 Too Low — Go Higher", "info"),
    "Win":      ("🎉 Correct!", "success"),
}

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
        "btn_text":    "#ffffff",
        "sidebar_bg":  "rgba(3,3,14,0.97)",
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
        "btn_text":    "#ffffff",
        "sidebar_bg":  "rgba(1,8,1,0.97)",
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
        "btn_text":    "#ffffff",
        "sidebar_bg":  "rgba(10,0,18,0.97)",
    },
}


def _hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def gv_color(value: int) -> str:
    t = THEMES.get(st.session_state.get("theme", "cyberpunk"), THEMES["cyberpunk"])
    return t["gv_high"] if value > 50 else (t["gv_mid"] if value > 20 else t["gv_low"])


def _make_label_chart(attempt: int, score: int, label: str, color: str, dy: int):
    """Return a single Altair text annotation for the score projection chart."""
    df = pd.DataFrame({"attempt": [attempt], "score": [score], "label": [label]})
    return (
        alt.Chart(df)
        .mark_text(align="left", dx=6, dy=dy, fontSize=11, fontWeight="bold", color=color)
        .encode(x=alt.X("attempt:Q"), y=alt.Y("score:Q"), text=alt.Text("label:N"))
    )


GV_TOOLTIP = (
    "Guess Volatility (GV) — bonus points awarded for winning. "
    "Bigger reward the earlier and faster you guess correctly. "
    "At the last attempt GV reaches 0."
)

st.set_page_config(page_title="Glitch Guesser", page_icon="🎮", layout="centered")

# Early init — sidebar reads these before the defaults dict runs
if "username" not in st.session_state:
    st.session_state.username = lb.generate_random_name()
if "username_locked" not in st.session_state:
    st.session_state.username_locked = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
attempt_limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
attempt_limit = attempt_limit_map[difficulty]
low, high = get_range_for_difficulty(difficulty)

# Reset game state when difficulty changes
if st.session_state.get("difficulty") != difficulty:
    st.session_state.difficulty = difficulty
    if "secret" in st.session_state:   # not first load
        for _k in ["secret", "attempts", "score", "status", "history",
                   "history_outcomes", "last_hint", "start_time",
                   "score_delta", "score_history", "_coach_hint", "_new_personal_best"]:
            st.session_state.pop(_k, None)

_theme_names = {k: v["name"] for k, v in THEMES.items()}
_selected_theme_name = st.sidebar.selectbox(
    "Theme",
    options=list(_theme_names.values()),
    index=list(_theme_names.values()).index(
        _theme_names.get(st.session_state.get("theme", "cyberpunk"), "Cyberpunk Neon")
    ),
)
st.session_state.theme = next(k for k, v in THEMES.items() if v["name"] == _selected_theme_name)

st.sidebar.divider()
st.sidebar.caption("Range"); st.sidebar.markdown(f"**{low} — {high}**")
st.sidebar.caption("Max Attempts"); st.sidebar.markdown(f"**{attempt_limit}**")

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
    "Anthropic API Key",
    type="password",
    placeholder="sk-ant-...",
    help="Your key is used only for this session and never stored.",
    key="user_api_key",
)
with st.sidebar.expander("How to get an API key"):
    st.markdown(
        "1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in\n"
        "2. Navigate to **API Keys** → **Create Key**\n"
        "3. Copy the key and paste it above"
    )

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "secret": random.randint(low, high),
    "attempts": 0, "score": 100, "status": "playing",
    "history": [], "history_outcomes": [], "game_id": 0, "last_hint": None,
    "start_time": time.time(), "score_delta": None,
    "score_history": [100],
    "username": lb.generate_random_name(),
    "username_locked": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Active theme + background cycling ────────────────────────────────────────
t = THEMES.get(st.session_state.get("theme", "cyberpunk"), THEMES["cyberpunk"])
bg = t["bg_tones"][st.session_state.attempts % len(t["bg_tones"])]

elapsed = int(time.time() - st.session_state.start_time)
penalty = 100 // attempt_limit
# attempts is 0-indexed (guesses made so far); pass guess number (1-indexed) so
# display and win calculation stay in sync — win uses post-incremented attempts.
gv_now  = guess_volatility(st.session_state.attempts + 1, attempt_limit, elapsed)

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
      color: {t["btn_text"]}; font-size: 0.85rem; font-weight: 700;
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
      background: {t["sidebar_bg"]} !important;
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

# ── Debug + live timer/GV injection ───────────────────────────────────────────
_dbg = json.dumps({
    "secret": st.session_state.secret, "attempts": st.session_state.attempts,
    "score": st.session_state.score, "difficulty": difficulty,
    "status": st.session_state.status, "history": st.session_state.history,
})
_start_ms   = int(st.session_state.start_time * 1000)
_attempts   = st.session_state.attempts + 1   # 1-indexed guess number
_limit      = attempt_limit
_is_playing = str(st.session_state.status == "playing").lower()

components.html(f"""
<script>
console.log('[DEBUG] Game State:', {_dbg});

(function() {{
  const START_MS     = {_start_ms};
  const ATTEMPTS     = {_attempts};
  const LIMIT        = {_limit};
  const IS_PLAYING   = {_is_playing};

  const GV_HIGH = '{t["gv_high"]}';
  const GV_MID  = '{t["gv_mid"]}';
  const GV_LOW  = '{t["gv_low"]}';
  function gvColor(v) {{
    return v > 50 ? GV_HIGH : v > 20 ? GV_MID : GV_LOW;
  }}

  function calcGV(elapsed) {{
    if (ATTEMPTS >= LIMIT) return 0;
    const remaining = 1.0 - (ATTEMPTS - 1) / Math.max(LIMIT - 1, 1);
    const f = Math.pow(remaining, 1.2);
    const tb = Math.max(0, Math.floor(100 * Math.max(0, 1 - elapsed / 120)));
    return Math.floor(400 * f) + tb;
  }}

  function tick() {{
    const elapsed = Math.floor((Date.now() - START_MS) / 1000);
    const doc = window.parent.document;

    const timeEl = doc.getElementById('live-time');
    if (timeEl) timeEl.textContent = elapsed + 's';

    if (IS_PLAYING) {{
      const gv    = calcGV(elapsed);
      const gvEl  = doc.getElementById('live-gv-value');
      if (gvEl) {{
        gvEl.textContent = '+' + gv;
        gvEl.style.color = gvColor(gv);
      }}
      // Update GV label inside the Altair chart SVG (cache after first find)
      if (!gvChartEl) {{
        const svgTexts = doc.querySelectorAll('.vega-embed svg text');
        for (const el of svgTexts) {{
          if (el.textContent && el.textContent.includes('GV')) {{
            gvChartEl = el;
            break;
          }}
        }}
      }}
      if (gvChartEl) {{
        gvChartEl.textContent = '+' + gv + ' GV';
        gvChartEl.setAttribute('fill', gvColor(gv));
      }}
    }}
  }}

  let gvChartEl = null;  // cached SVG text node for GV label

  let started = false;
  function start() {{
    if (started) return;
    const doc = window.parent.document;
    if (!doc.getElementById('live-time') || !doc.getElementById('live-gv-value')) {{
      setTimeout(start, 100);
      return;
    }}
    started = true;
    tick();
    setInterval(tick, 1000);
  }}
  setTimeout(start, 80);
}})();
</script>
""", height=0)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_game, tab_board = st.tabs(["🎮 Game", "🏆 Leaderboard"])

with tab_game:
    # ── Header ────────────────────────────────────────────────────────────────
    st.title("🎮 Glitch Guesser")

    # ── Win / Loss banner ─────────────────────────────────────────────────────
    if st.session_state.status == "won":
        st.success(f"🏆 Won! Secret: **{st.session_state.secret}** · {elapsed}s · Score: **{st.session_state.score}**")
        if st.session_state.pop("_new_personal_best", False):
            st.success("🌟 New personal best — score saved to leaderboard!")
    elif st.session_state.status == "lost":
        st.error(f"💀 Out of attempts! Secret was **{st.session_state.secret}**. Score: **{st.session_state.score}**")

    # ── TOP SECTION: stats (15%) | GV + chart (85%) ───────────────────────────
    top_stats, top_main = st.columns([15, 85])

    with top_stats:
        st.metric("Score", st.session_state.score,
                  delta=st.session_state.score_delta, delta_color="normal")
        st.metric("Attempts", f"{st.session_state.attempts} / {attempt_limit}")
        st.markdown(
            f'<div style="padding:4px 0 8px 0;">'
            f'<div style="font-size:0.75rem;color:{t["muted"]};margin-bottom:2px;letter-spacing:0.08em;">TIME</div>'
            f'<div id="live-time" style="font-size:1.75rem;font-weight:700;color:{t["accent"]};font-family:\'{t["font_body"]}\',monospace;text-shadow:0 0 10px {t["accent"]}80;">{elapsed}s</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with top_main:
        # GV info box
        gv_color_val = gv_color(gv_now)
        st.markdown(
            f'<div title="{GV_TOOLTIP}" style="background:{t["card_bg"]};'
            f'border:1px solid {t["border"]};border-radius:4px;padding:8px 12px;cursor:help;margin-bottom:8px;">'
            f'<span style="font-size:0.7rem;color:{t["muted"]};letter-spacing:0.1em;">GUESS VOLATILITY (?)</span><br>'
            f'<span id="live-gv-value" style="font-size:1.4rem;font-weight:700;color:{gv_color_val};font-family:\'{t["font_body"]}\',monospace;">+{gv_now}</span>'
            f'<span style="font-size:0.8rem;color:{t["muted"]};"> pts if you win now</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Score projection chart — show from game start (even before first guess)
        hist = st.session_state.score_history
        if len(hist) >= 1:
            n = len(hist) - 1
            current_score = hist[-1]

            actual_df = pd.DataFrame({
                "attempt": list(range(len(hist))),
                "score":   hist,
                "series":  "Score",
            })

            if st.session_state.status == "playing":
                win_score  = current_score + gv_now
                lose_score = max(0, current_score - penalty)
                proj_df = pd.DataFrame({
                    "attempt": [n, n + 1, n, n + 1],
                    "score":   [current_score, win_score, current_score, lose_score],
                    "series":  ["Win ▲", "Win ▲", "Lose ▼", "Lose ▼"],
                })
                chart_df = pd.concat([actual_df, proj_df], ignore_index=True)
            else:
                chart_df = actual_df

            color_scale = alt.Scale(
                domain=["Score", "Win ▲", "Lose ▼"],
                range=[t["chart_score"], t["chart_win"], t["chart_lose"]],
            )

            base = (
                alt.Chart(chart_df)
                .mark_line(point=True, strokeWidth=2)
                .encode(
                    x=alt.X("attempt:Q", title=None, axis=alt.Axis(tickMinStep=1, labelColor=t["muted"], gridColor=t["border"])),
                    y=alt.Y("score:Q", title=None,
                            scale=alt.Scale(domain=[0, max(130, current_score + gv_now + 20)]),
                            axis=alt.Axis(labelColor=t["muted"], gridColor=t["border"])),
                    color=alt.Color("series:N", scale=color_scale,
                                    legend=alt.Legend(title=None, labelColor=t["text"])),
                    strokeDash=alt.condition(
                        alt.datum.series == "Score",
                        alt.value([1, 0]), alt.value([5, 3])
                    ),
                    tooltip=[
                        alt.Tooltip("attempt:Q", title="Attempt"),
                        alt.Tooltip("score:Q",   title="Score"),
                        alt.Tooltip("series:N",  title="Series"),
                    ],
                )
                .properties(height=160)
            )

            # GV label at the Win ▲ tip + score label at Lose ▼ tip
            if st.session_state.status == "playing":
                base = (
                    base
                    + _make_label_chart(n + 1, win_score,  f"+{gv_now} GV",     gv_color(gv_now), dy=-6)
                    + _make_label_chart(n + 1, lose_score, f"{lose_score} pts", t["chart_lose"], dy=8)
                )

            chart = base.properties(background="transparent").configure_view(strokeOpacity=0)

            st.altair_chart(chart, use_container_width=True)

    st.divider()

    # ── Show Hints toggle + hint feedback ─────────────────────────────────────
    show_hints = st.checkbox("Show Hints", value=True, key="show_hints")
    if show_hints and st.session_state.last_hint:
        label, kind = HINT_MESSAGES[st.session_state.last_hint]
        {"success": st.success, "warning": st.warning, "info": st.info}[kind](label)

    # ── BOTTOM SECTION: guess form (left) | history (right) ──────────────────
    bot_left, bot_right = st.columns([1, 1], gap="medium")

    with bot_left:
        if st.session_state.status == "playing":
            with st.form("guess_form"):
                raw_guess = st.text_input(
                    f"Guess ({low}–{high})",
                    placeholder=f"{low}–{high}",
                    key=f"gi_{difficulty}_{st.session_state.game_id}",
                )
                submit = st.form_submit_button(
                    "Submit Guess", use_container_width=True, type="primary"
                )

            if submit:
                ok, guess_val, err = parse_guess(raw_guess)
                if not ok:
                    st.error(err)
                elif guess_val < low or guess_val > high:
                    st.error(f"⚠️ Must be between {low} and {high}. No attempt used.")
                else:
                    st.session_state.attempts += 1
                    outcome = check_guess(guess_val, st.session_state.secret)
                    st.session_state.history.append(guess_val)
                    st.session_state.history_outcomes.append(outcome)
                    st.session_state.last_hint = outcome
                    prev = st.session_state.score

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
                    else:
                        st.session_state.score = update_score(prev, outcome, penalty)
                        st.session_state.score_delta = -penalty
                        if st.session_state.attempts >= attempt_limit:
                            st.session_state.score = 0  # absorb remainder from integer division
                            st.session_state.status = "lost"

                    st.session_state.score_history.append(st.session_state.score)
                    st.rerun()

        # ── AI Coach ──────────────────────────────────────────────────────────
        if st.session_state.status == "playing":
            st.markdown("---")
            with st.expander("🤖 Ask AI Coach", expanded=False):
                st.caption(
                    "The coach analyses your guesses and suggests the mathematically optimal "
                    "next number using binary search strategy."
                )
                if st.button("Get Coach Hint", key="coach_btn", use_container_width=True):
                    with st.spinner("Coach thinking…"):
                        hint = get_coach_hint(
                            low=low,
                            high=high,
                            attempts_used=st.session_state.attempts,
                            attempt_limit=attempt_limit,
                            history=st.session_state.history,
                            outcomes=st.session_state.history_outcomes,
                            api_key=st.session_state.get("user_api_key") or None,
                        )
                    st.session_state["_coach_hint"] = hint

                if "_coach_hint" in st.session_state:
                    h = st.session_state["_coach_hint"]
                    if h.get("suggestion") is not None:
                        st.markdown(
                            f'<div style="background:{t["card_bg"]};border:1px solid {t["border"]};border-radius:4px;'
                            f'padding:10px 14px;margin-top:6px;">'
                            f'<div style="font-size:0.7rem;color:{t["muted"]};letter-spacing:0.1em;margin-bottom:4px;">RECOMMENDED GUESS</div>'
                            f'<div style="font-size:2.2rem;font-weight:700;color:{t["accent"]};font-family:\'{t["font_body"]}\',monospace;text-shadow:0 0 12px {t["accent"]}80;">{h["suggestion"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    conf_pct = int(h.get("confidence", 0) * 100)
                    conf_color = t["gv_high"] if conf_pct > 60 else (t["accent"] if conf_pct > 30 else t["gv_low"])
                    st.markdown(
                        f'<div style="font-size:0.8rem;color:{conf_color};margin-top:4px;">'
                        f'Confidence: {conf_pct}%</div>',
                        unsafe_allow_html=True,
                    )
                    if h.get("strategy_tip"):
                        st.info(h["strategy_tip"])
                    if h.get("reasoning"):
                        st.caption(h["reasoning"])

        # New Game button sits below the guess form
        if st.button("New Game", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state.game_id += 1
            st.session_state.secret = random.randint(low, high)
            st.session_state.start_time = time.time()
            st.session_state.pop("_coach_hint", None)
            st.rerun()

    with bot_right:
        st.subheader("History")

        # Color legend
        st.markdown(
            f'<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;">'
            f'<span style="font-size:0.7rem;background:{_hex_rgba(t["accent2"], 0.15)};color:{t["accent2"]};'
            f'border:1px solid {t["accent2"]}66;border-radius:3px;padding:2px 8px;letter-spacing:0.06em;">▼ TOO LOW</span>'
            f'<span style="font-size:0.7rem;background:{t["card_bg"]};color:{t["accent"]};'
            f'border:1px solid {t["border"]};border-radius:3px;padding:2px 8px;letter-spacing:0.06em;">▲ TOO HIGH</span>'
            f'<span style="font-size:0.7rem;background:{_hex_rgba(t["gv_high"], 0.1)};color:{t["gv_high"]};'
            f'border:1px solid {t["gv_high"]}66;border-radius:3px;padding:2px 8px;letter-spacing:0.06em;">✓ CORRECT</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        CHIP_COLORS = {
            "Too Low":  (_hex_rgba(t["accent2"], 0.18),  t["accent2"]),
            "Too High": (t["card_bg"],                   t["accent"]),
            "Win":      (_hex_rgba(t["gv_high"], 0.15),  t["gv_high"]),
        }
        if st.session_state.history:
            chips = " ".join(
                '<span style="display:inline-block;border-radius:20px;padding:2px 10px;'
                f'margin:2px;font-size:0.82rem;background:{CHIP_COLORS[o][0]};'
                f'color:{CHIP_COLORS[o][1]};border:1px solid {CHIP_COLORS[o][1]}40;">'
                f'{g}</span>'
                for g, o in zip(st.session_state.history, st.session_state.history_outcomes)
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.caption("No guesses yet.")

with tab_board:
    st.markdown("### 🏆 Top Players")
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

