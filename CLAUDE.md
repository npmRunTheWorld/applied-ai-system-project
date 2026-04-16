# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Input Files

All user-provided instruction files live in **`.claude/inputs/`** inside the project root (e.g. `.claude/inputs/STEPS.md`). Read from there at the start of any session where the user says "instructions are in inputs.<FILE>".

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
python -m streamlit run app.py

# Run tests
pytest

# Run a single test
pytest tests/test_game_logic.py::test_winning_guess
```

## Project Overview

This is a **intentionally buggy** Streamlit number-guessing game used as an educational exercise. The goal is for students to find and fix the bugs, then refactor logic into `logic_utils.py`.

### Known Bugs (by design)

1. **Wrong hints** — `check_guess` in `app.py` returns "Go HIGHER!" when the guess is too high, and "Go LOWER!" when too low (inverted).
2. **Score logic bug** — `update_score` gives +5 points on even-numbered "Too High" guesses instead of penalizing.
3. **Hard difficulty range bug** — `get_range_for_difficulty("Hard")` returns `(1, 50)` but uses the same 1–100 range in the "Make a guess" info text (hardcoded to 100 instead of `high`).
4. **New Game resets attempts to 0** — but initial state sets attempts to 1, causing inconsistency.

### Architecture

- **`app.py`** — Streamlit UI and all game logic (currently duplicated with `logic_utils.py`). Uses `st.session_state` for `secret`, `attempts`, `score`, `status`, and `history`.
- **`logic_utils.py`** — Stub file where the four pure logic functions should be moved: `get_range_for_difficulty`, `parse_guess`, `check_guess`, `update_score`. All currently raise `NotImplementedError`.
- **`tests/test_game_logic.py`** — Tests import from `logic_utils`. Tests expect `check_guess` to return just the outcome string (e.g., `"Win"`), not a tuple.

- **`claude/**` - Has all claude related files like .md which it can use as context and read from

### Refactor Target

The assignment requires moving logic from `app.py` into `logic_utils.py` and making `pytest` pass. Note that tests call `check_guess(guess, secret)` and assert on the outcome string only — the current `app.py` implementation returns a tuple `(outcome, message)`, so the API must be reconciled when refactoring.


# GIT INSTRUCTIONS
1. Each feature worked in should be on a different branch titled the bug fix and number and pushed to that origin with intial state before working on it.  

2. When creating branch for a specific issue they will need a action/tag-number, action here is like fix, refactor, feature where tag is the problem like arch, bug, ui, dep, and the number is the association to the order of the bug found.

3. 
   3a. Upon completion of a feature, fix, refactor. First sumarize what was done and all the files that were targeted and give a small file/line range, addition, subraction changes report.
   3b.Then do unit tests and upon success. Tell the user to CHECK LOCALHOST. 
   3c.Then push all code to the branch. And ask to open a PR to the main branch.


# Mid session
1. Create git commit -m "pre-agent checkpoints" per MAJOR thoughts or ideas. That can be reversed in the future. Most feature works takes somewhere betweeen 50-300 lines of code changes.



# At end of session
1. "Summarize what we accomplished, whats in progress, and the next steps. Write this to claude/SESSION_NOTES.md"

2. Ask for a code review of the recent changes with /review


4. Finally ask for Pr 


# Start of next session
1. "Read SESSION_NOTES.md and the CLAUDE.md file then continue where left off on the task or the current instruction given"

2. Start in plan mode and ask quick questions that may be overlooked from the current plan using the SESSION_NOTES.md as context.


## Memory mangement and token optimzations
1. /compact the session to to include the most important of chagnes and exclude any repititions etc.

2. Go over CONTEXT.md to see if there are any contexts that are given. This may include full files, however it may also include ranges like Read lines from range x-y for a file. Instead of reading entire files read what is necessary

3. Limit bash output show failures only sumamrized to whats relevant instead of a whole large terminal reponse which may use a lot of tokens. 

4. Targeted grep (not whole repo):
"Search only src/api/ for usages of getUser"



# Orchestrator Prompt
"Spawn 3 agents"
1. Agent PM: who finds bugs and issues within the site and adds it to claude/BUGLOGS.md
2. Agent developer: who writes code and implements said changes from Agent PM and then finally once completed hand it over to the QA agent 
3. Agent QA: already understands the problems from agent PM. And works simultaneosly to create a framework to TEST the code from Agent developer. Which you can also inform the agent developer mid way
