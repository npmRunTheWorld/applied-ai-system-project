"""
ai_coach.py — AI Game Coach using Claude API (Agentic Workflow)

The coach runs a manual tool-use loop:
  1. narrow_range    → computes current valid guess range from history
  2. suggest_binary_search → picks optimal next guess (binary search midpoint)
  3. evaluate_strategy     → scores how efficiently the player has been guessing

All interactions are logged to logs/coach_log.jsonl for reliability auditing.
"""

import json
import time
import logging
from pathlib import Path

import anthropic

# ── Logging setup ─────────────────────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
_COACH_LOG = LOG_DIR / "coach_log.jsonl"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_logger = logging.getLogger(__name__)

# ── Claude client ─────────────────────────────────────────────────────────────
_client = anthropic.Anthropic()

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "narrow_range",
        "description": (
            "Given the initial range and the player's guess history with outcomes, "
            "compute the current valid range the secret number must be in."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "low":      {"type": "integer", "description": "Initial lower bound (inclusive)"},
                "high":     {"type": "integer", "description": "Initial upper bound (inclusive)"},
                "history":  {"type": "array", "items": {"type": "integer"}, "description": "Previous guesses in order"},
                "outcomes": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["Too High", "Too Low", "Win"]},
                    "description": "Outcome for each guess (parallel with history)",
                },
            },
            "required": ["low", "high", "history", "outcomes"],
        },
    },
    {
        "name": "suggest_binary_search",
        "description": (
            "Given the current valid range, suggest the mathematically optimal next guess "
            "using binary search (midpoint rounding toward center)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "current_low":  {"type": "integer", "description": "Current lower bound (inclusive)"},
                "current_high": {"type": "integer", "description": "Current upper bound (inclusive)"},
            },
            "required": ["current_low", "current_high"],
        },
    },
    {
        "name": "evaluate_strategy",
        "description": (
            "Evaluate how efficiently the player has been guessing by comparing their "
            "actual range narrowing to the ideal binary-search pace."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "attempts_used":   {"type": "integer", "description": "Number of guesses made so far"},
                "attempt_limit":   {"type": "integer", "description": "Maximum allowed guesses"},
                "initial_range":   {"type": "integer", "description": "Total initial range size (high - low + 1)"},
                "current_range":   {"type": "integer", "description": "Remaining range size after narrowing"},
            },
            "required": ["attempts_used", "attempt_limit", "initial_range", "current_range"],
        },
    },
]


# ── Pure tool implementations (testable without API) ─────────────────────────

def _narrow_range(low: int, high: int, history: list[int], outcomes: list[str]) -> dict:
    """Narrow the valid range based on guess history."""
    curr_low, curr_high = low, high
    for guess, outcome in zip(history, outcomes):
        if outcome == "Too High":
            curr_high = min(curr_high, guess - 1)
        elif outcome == "Too Low":
            curr_low = max(curr_low, guess + 1)
    return {"current_low": curr_low, "current_high": curr_high}


def _suggest_binary_search(current_low: int, current_high: int) -> dict:
    """Return the binary-search midpoint for a range."""
    suggestion = (current_low + current_high) // 2
    return {"suggestion": suggestion}


def _evaluate_strategy(
    attempts_used: int,
    attempt_limit: int,
    initial_range: int,
    current_range: int,
) -> dict:
    """Score the player's range-narrowing efficiency (0.0 – 1.0)."""
    if attempts_used == 0:
        return {"efficiency": 1.0, "comment": "Game just started — no guesses yet."}

    # Ideal: each guess halves the range
    ideal_remaining = initial_range / (2 ** attempts_used)
    if ideal_remaining <= 0 or current_range <= 0:
        efficiency = 1.0
    else:
        efficiency = min(1.0, round(ideal_remaining / current_range, 2))

    if efficiency >= 0.85:
        comment = "Excellent — you're tracking binary search pace!"
    elif efficiency >= 0.5:
        comment = "Decent, but binary search would narrow faster."
    else:
        comment = "Try guessing the midpoint of the remaining range each time."

    return {"efficiency": efficiency, "comment": comment}


def _dispatch_tool(name: str, inputs: dict) -> dict:
    """Route a tool-use block to the right local function."""
    if name == "narrow_range":
        return _narrow_range(
            inputs["low"], inputs["high"],
            inputs["history"], inputs["outcomes"],
        )
    if name == "suggest_binary_search":
        return _suggest_binary_search(inputs["current_low"], inputs["current_high"])
    if name == "evaluate_strategy":
        return _evaluate_strategy(
            inputs["attempts_used"], inputs["attempt_limit"],
            inputs["initial_range"], inputs["current_range"],
        )
    return {"error": f"Unknown tool: {name}"}


# ── Main entry point ──────────────────────────────────────────────────────────

def get_coach_hint(
    low: int,
    high: int,
    attempts_used: int,
    attempt_limit: int,
    history: list[int],
    outcomes: list[str],
) -> dict:
    """
    Run the AI coach agentic loop and return a hint.

    Returns a dict with keys:
      - suggestion  : int | None   — recommended next guess
      - reasoning   : str          — Claude's explanation
      - confidence  : float        — 0.0–1.0, based on range narrowing progress
      - strategy_tip: str          — efficiency feedback from evaluate_strategy
    """
    t0 = time.time()
    tool_results_store: dict = {}

    system = (
        "You are an expert number-guessing game coach. "
        "Your job is to help players find the secret number as efficiently as possible "
        "using binary search strategy. "
        "Always use your tools in this order: "
        "1) narrow_range to find the current valid range, "
        "2) suggest_binary_search to pick the optimal next guess, "
        "3) evaluate_strategy to rate the player's progress. "
        "Then summarize your recommendation in 1–2 sentences."
    )

    history_summary = (
        list(zip(history, outcomes)) if history else "No guesses yet"
    )
    user_message = (
        f"Range: [{low}, {high}] | "
        f"Attempts: {attempts_used}/{attempt_limit} | "
        f"History: {history_summary}. "
        "Please analyse the game state and tell me my best next guess."
    )

    messages = [{"role": "user", "content": user_message}]
    reasoning = ""
    suggestion = None
    confidence = 0.0
    strategy_tip = ""

    try:
        # Agentic loop — max 6 iterations to prevent runaway cost
        for _ in range(6):
            response = _client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        reasoning = block.text
                break

            if response.stop_reason == "tool_use":
                tool_calls = [b for b in response.content if b.type == "tool_use"]
                tool_results_content = []

                for tc in tool_calls:
                    result = _dispatch_tool(tc.name, tc.input)
                    tool_results_store[tc.name] = result
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps(result),
                    })

                    # Capture values as they arrive
                    if tc.name == "suggest_binary_search":
                        suggestion = result.get("suggestion")
                    if tc.name == "evaluate_strategy":
                        strategy_tip = result.get("comment", "")

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user",      "content": tool_results_content})
            else:
                # pause_turn or unexpected — stop cleanly
                break

    except anthropic.APIError as exc:
        _logger.error("Coach API error: %s", exc)
        reasoning = "Coach unavailable — API error."
    except Exception as exc:
        _logger.error("Coach unexpected error: %s", exc)
        reasoning = "Coach unavailable."

    # Derive confidence from how much the range has narrowed
    nr = tool_results_store.get("narrow_range", {})
    curr_low  = nr.get("current_low",  low)
    curr_high = nr.get("current_high", high)
    total_range   = max(1, high - low + 1)
    current_range = max(1, curr_high - curr_low + 1)

    if current_range == 1:
        confidence = 1.0
    else:
        confidence = round(1.0 - (current_range / total_range), 2)

    elapsed = round(time.time() - t0, 2)

    # Write interaction to JSONL log
    log_entry = {
        "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_s":   elapsed,
        "game_state": {
            "low": low, "high": high,
            "attempts_used": attempts_used, "attempt_limit": attempt_limit,
            "history": history, "outcomes": outcomes,
        },
        "result": {
            "suggestion":   suggestion,
            "confidence":   confidence,
            "strategy_tip": strategy_tip,
        },
    }
    try:
        with open(_COACH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except OSError as exc:
        _logger.warning("Could not write coach log: %s", exc)

    return {
        "suggestion":   suggestion,
        "reasoning":    reasoning,
        "confidence":   confidence,
        "strategy_tip": strategy_tip,
    }
