"""
Tests for ai_coach.py internal tool functions.
No real API calls — validates the pure logic behind the agentic tools.
"""
import pytest
from ai_coach import _narrow_range, _suggest_binary_search, _evaluate_strategy


# ── narrow_range ──────────────────────────────────────────────────────────────

def test_narrow_range_no_history():
    result = _narrow_range(1, 100, [], [])
    assert result == {"current_low": 1, "current_high": 100}


def test_narrow_range_too_high():
    # Guessed 70, told Too High → secret < 70
    result = _narrow_range(1, 100, [70], ["Too High"])
    assert result["current_high"] == 69
    assert result["current_low"] == 1


def test_narrow_range_too_low():
    # Guessed 30, told Too Low → secret > 30
    result = _narrow_range(1, 100, [30], ["Too Low"])
    assert result["current_low"] == 31
    assert result["current_high"] == 100


def test_narrow_range_combined():
    # Guessed 30 Too Low, then 70 Too High → range is [31, 69]
    result = _narrow_range(1, 100, [30, 70], ["Too Low", "Too High"])
    assert result["current_low"] == 31
    assert result["current_high"] == 69


def test_narrow_range_win_does_not_change_range():
    # Win outcome should not alter bounds
    result = _narrow_range(1, 100, [50], ["Win"])
    assert result == {"current_low": 1, "current_high": 100}


# ── suggest_binary_search ─────────────────────────────────────────────────────

def test_binary_search_full_range():
    result = _suggest_binary_search(1, 100)
    assert result["suggestion"] == 50


def test_binary_search_narrow_range():
    result = _suggest_binary_search(31, 69)
    assert result["suggestion"] == 50


def test_binary_search_single_value():
    result = _suggest_binary_search(42, 42)
    assert result["suggestion"] == 42


def test_binary_search_two_values():
    # Floor division: (1 + 2) // 2 = 1
    result = _suggest_binary_search(1, 2)
    assert result["suggestion"] == 1


# ── evaluate_strategy ─────────────────────────────────────────────────────────

def test_evaluate_strategy_no_guesses():
    result = _evaluate_strategy(0, 8, 100, 100)
    assert result["efficiency"] == 1.0
    assert "started" in result["comment"].lower()


def test_evaluate_strategy_perfect_binary_search():
    # After 1 ideal guess: range should be 50 out of 100
    result = _evaluate_strategy(1, 8, 100, 50)
    # ideal = 100 / 2 = 50; current = 50 → efficiency = 1.0
    assert result["efficiency"] == 1.0


def test_evaluate_strategy_poor_narrowing():
    # After 3 guesses, player still has 90 out of 100 remaining
    result = _evaluate_strategy(3, 8, 100, 90)
    # ideal = 100 / 8 = 12.5; current = 90 → well below 1.0
    assert result["efficiency"] < 0.5
    assert "binary search" in result["comment"].lower() or "midpoint" in result["comment"].lower()


def test_evaluate_strategy_efficiency_capped_at_one():
    # Even if player somehow narrowed more than ideal, cap at 1.0
    result = _evaluate_strategy(1, 8, 100, 1)
    assert result["efficiency"] <= 1.0


def test_evaluate_strategy_returns_comment():
    result = _evaluate_strategy(2, 8, 100, 30)
    assert "comment" in result
    assert isinstance(result["comment"], str)
