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
