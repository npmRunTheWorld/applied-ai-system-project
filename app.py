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

HINT_MESSAGES = {
    "Too High": ("📉 Too High — Go Lower", "warning"),
    "Too Low":  ("📈 Too Low — Go Higher", "info"),
    "Win":      ("🎉 Correct!", "success"),
}

# Dark background tones — cycle with each guess
BG_TONES = [
    "#0d0d1a", "#0a0f14", "#0a140f", "#14100a",
    "#140a0a", "#0a1414", "#100a14", "#14140a",
]

def gv_color(value: int) -> str:
    """Return hex color for a GV value (mirrors JS gvColor)."""
    return "#2CA02C" if value > 50 else ("#FFA500" if value > 20 else "#D62728")


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

# ── Sidebar ───────────────────────────────────────────────────────────────────
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
attempt_limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
attempt_limit = attempt_limit_map[difficulty]
low, high = get_range_for_difficulty(difficulty)

st.sidebar.divider()
st.sidebar.caption("Range"); st.sidebar.markdown(f"**{low} — {high}**")
st.sidebar.caption("Max Attempts"); st.sidebar.markdown(f"**{attempt_limit}**")

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "secret": random.randint(low, high),
    "attempts": 0, "score": 100, "status": "playing",
    "history": [], "history_outcomes": [], "game_id": 0, "last_hint": None,
    "start_time": time.time(), "score_delta": None,
    "score_history": [100],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Background cycling ────────────────────────────────────────────────────────
bg = BG_TONES[st.session_state.attempts % len(BG_TONES)]

elapsed = int(time.time() - st.session_state.start_time)
penalty = 100 // attempt_limit
# attempts is 0-indexed (guesses made so far); pass guess number (1-indexed) so
# display and win calculation stay in sync — win uses post-incremented attempts.
gv_now  = guess_volatility(st.session_state.attempts + 1, attempt_limit, elapsed)

st.markdown(f"""
<style>
  .stApp {{ background-color: {bg}; transition: background-color 0.8s ease; }}
  .stApp, .stApp p, .stApp label, .stApp span, .stApp div {{
      color: #e8e8f0 !important;
  }}
  .block-container {{ padding-top: 1.2rem; max-width: 860px; }}
  h1 {{ font-size: 1.6rem !important; font-weight: 700; color: #ffffff !important; }}
  div[data-testid="stForm"] {{ border: none; padding: 0; }}
  .guess-chip {{
      display: inline-block; background: rgba(255,255,255,0.1);
      border-radius: 20px; padding: 1px 10px; margin: 2px;
      font-size: 0.82rem; color: #ccc;
  }}
  div[data-testid="stFormSubmitButton"] button {{
      background: linear-gradient(135deg, #00b09b 0%, #ff6348 100%);
      color: #fff; font-size: 0.95rem; font-weight: 600;
      letter-spacing: 0.06em; border: none; border-radius: 10px;
      padding: 0.6rem 1.4rem;
      box-shadow: 0 4px 14px rgba(0,176,155,0.4);
      transition: all 0.2s ease;
  }}
  div[data-testid="stFormSubmitButton"] button:hover {{
      box-shadow: 0 6px 20px rgba(255,99,72,0.5); transform: translateY(-1px);
  }}
  div[data-testid="stFormSubmitButton"] button:active {{
      transform: translateY(0); box-shadow: 0 2px 8px rgba(0,176,155,0.3);
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

  function gvColor(v) {{
    return v > 50 ? '#2CA02C' : v > 20 ? '#FFA500' : '#D62728';
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

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🎮 Glitch Guesser")

# ── Win / Loss banner ─────────────────────────────────────────────────────────
if st.session_state.status == "won":
    st.success(f"🏆 Won! Secret: **{st.session_state.secret}** · {elapsed}s · Score: **{st.session_state.score}**")
elif st.session_state.status == "lost":
    st.error(f"💀 Out of attempts! Secret was **{st.session_state.secret}**. Score: **{st.session_state.score}**")

# ── TOP SECTION: stats (15%) | GV + chart (85%) ───────────────────────────────
top_stats, top_main = st.columns([15, 85])

with top_stats:
    st.metric("Score", st.session_state.score,
              delta=st.session_state.score_delta, delta_color="normal")
    st.metric("Attempts", f"{st.session_state.attempts} / {attempt_limit}")
    st.markdown(
        f'<div style="padding:4px 0 8px 0;">'
        f'<div style="font-size:0.875rem;color:#9e9e9e;margin-bottom:2px;">Time</div>'
        f'<div id="live-time" style="font-size:1.75rem;font-weight:700;color:#fafafa;">{elapsed}s</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with top_main:
    # GV info box
    gv_color_val = gv_color(gv_now)
    st.markdown(
        f'<div title="{GV_TOOLTIP}" style="background:rgba(255,255,255,0.07);'
        f'border-radius:8px;padding:8px 12px;cursor:help;margin-bottom:8px;">'
        f'<span style="font-size:0.75rem;color:#aaa;">Guess Volatility (?)</span><br>'
        f'<span id="live-gv-value" style="font-size:1.4rem;font-weight:700;color:{gv_color_val};">+{gv_now}</span>'
        f'<span style="font-size:0.8rem;color:#aaa;"> pts if you win now</span>'
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
            range=["#748FFC", "#2CA02C", "#D62728"],
        )

        base = (
            alt.Chart(chart_df)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("attempt:Q", title=None, axis=alt.Axis(tickMinStep=1, labelColor="#aaa", gridColor="#333")),
                y=alt.Y("score:Q", title=None,
                        scale=alt.Scale(domain=[0, max(130, current_score + gv_now + 20)]),
                        axis=alt.Axis(labelColor="#aaa", gridColor="#333")),
                color=alt.Color("series:N", scale=color_scale,
                                legend=alt.Legend(title=None, labelColor="#ccc")),
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
                + _make_label_chart(n + 1, lose_score, f"{lose_score} pts",  "#D62728",        dy=8)
            )

        chart = base.properties(background="transparent").configure_view(strokeOpacity=0)

        st.altair_chart(chart, use_container_width=True)

st.divider()

# ── Show Hints toggle + hint feedback ─────────────────────────────────────────
show_hints = st.checkbox("Show Hints", value=True, key="show_hints")
if show_hints and st.session_state.last_hint:
    label, kind = HINT_MESSAGES[st.session_state.last_hint]
    {"success": st.success, "warning": st.warning, "info": st.info}[kind](label)

# ── BOTTOM SECTION: guess form (left) | history (right) ──────────────────────
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
                else:
                    st.session_state.score = update_score(prev, outcome, penalty)
                    st.session_state.score_delta = -penalty
                    if st.session_state.attempts >= attempt_limit:
                        st.session_state.score = 0  # absorb remainder from integer division
                        st.session_state.status = "lost"

                st.session_state.score_history.append(st.session_state.score)
                st.rerun()

    # ── AI Coach ──────────────────────────────────────────────────────────────
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
                    )
                st.session_state["_coach_hint"] = hint

            if "_coach_hint" in st.session_state:
                h = st.session_state["_coach_hint"]
                if h.get("suggestion") is not None:
                    st.markdown(
                        f'<div style="background:rgba(255,255,255,0.06);border-radius:8px;'
                        f'padding:10px 14px;margin-top:6px;">'
                        f'<div style="font-size:0.75rem;color:#aaa;margin-bottom:2px;">Recommended guess</div>'
                        f'<div style="font-size:2rem;font-weight:700;color:#748FFC;">{h["suggestion"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                conf_pct = int(h.get("confidence", 0) * 100)
                conf_color = "#2CA02C" if conf_pct > 60 else ("#FFA500" if conf_pct > 30 else "#D62728")
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
        '<div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;">'
        '<span style="font-size:0.75rem;background:rgba(214,39,40,0.2);color:#e07070;'
        'border:1px solid #e0707040;border-radius:12px;padding:1px 8px;">🔴 Too Low</span>'
        '<span style="font-size:0.75rem;background:rgba(44,160,44,0.2);color:#6fcf6f;'
        'border:1px solid #6fcf6f40;border-radius:12px;padding:1px 8px;">🟢 Too High</span>'
        '<span style="font-size:0.75rem;background:rgba(255,193,7,0.2);color:#ffd54f;'
        'border:1px solid #ffd54f40;border-radius:12px;padding:1px 8px;">🟡 Correct</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    CHIP_COLORS = {
        "Too Low":  ("rgba(214,39,40,0.25)",  "#e07070"),   # red   — guessed too low
        "Too High": ("rgba(44,160,44,0.25)",   "#6fcf6f"),  # green — guessed too high
        "Win":      ("rgba(255,193,7,0.25)",   "#ffd54f"),  # gold  — correct
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

