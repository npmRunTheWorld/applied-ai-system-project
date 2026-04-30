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
    assert len(board) == 1
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
    assert board[0]["score"] == 200


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
