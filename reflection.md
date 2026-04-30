# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the secret number kept changing" or "the hints were backwards").

When I first ran the game, the UI loaded but almost immediately felt off — the hints were completely backwards, so if my guess was too high it told me to go higher, which made the game unwinnable in a logical way. The difficulty ranges were also wrong: Easy was 1–20, Normal stretched all the way to 1–100, and Hard was only 1–50, which made Hard actually easier than Normal in terms of range size. On top of that, a wrong guess could still award bonus points because the score logic was checking even-numbered attempts and rewarding them regardless of outcome. When I clicked New Game, the score didn't reset either — it just kept accumulating from the previous session, which made the leaderboard meaningless from the start.


---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).

I used Claude Code as my primary AI tool throughout the project, with ChatGPT on the side for quick conceptual questions when I didn't want to burn context. For the bigger feature work I actually spawned multiple Claude subagents — one acting as a PM to identify bugs and write specs, a developer agent to implement changes, and a QA agent that wrote the tests and verified the output independently. One example where AI got it exactly right was when it suggested wrapping `random.randint()` inside `if "secret" not in st.session_state` to stabilize the secret number — I verified it by submitting a guess, watching the number not change on rerun, and running the tests. One area where I had to push back was when an early agent implementation tried to catch all `anthropic.APIError` exceptions with a single generic message — it was technically correct but unhelpful in practice, because when my API credits ran out the error just said "API error" with no actionable information. I caught that during manual testing and had it update the error handling to surface the actual billing message.

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

I used a two-step check for every fix: pytest had to pass first, and then I'd manually verify the behaviour in the browser at localhost before considering it done. The most useful individual test was `test_guess_too_high`, which calls `check_guess(60, 50)` and asserts the return value is the string `"Too High"` — before the fix, `logic_utils.py` raised `NotImplementedError` because the functions were stubs, and after the refactor it passed cleanly. That test also surfaced an API mismatch: the original `app.py` returned a tuple `(outcome, message)` from `check_guess`, but the tests expected just a plain string, which forced me to reconcile the interface properly rather than just making it "work somehow." The QA agent was genuinely useful here because it wrote the tests before the implementation existed, which meant I had a clear contract to code against instead of retrofitting tests afterward.

---


## 4. What did you learn about Streamlit and state?

- In your own words, explain why the secret number kept changing in the original app.
- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?
- What change did you make that finally gave the game a stable secret number?

The secret kept changing because `random.randint()` was sitting at the top of the script with no protection — every time a user clicked a button or typed anything, Streamlit re-ran the entire Python file from scratch, which called `random.randint()` again and generated a brand new number. The way I'd explain Streamlit to someone who hasn't used it: imagine your whole app is a recipe that gets cooked fresh every time someone touches a dial on the stove — `session_state` is like a sticky note on the fridge that survives each re-cook so you can remember things between runs. The fix was wrapping the secret generation inside `if "secret" not in st.session_state`, which means it only runs once on the very first load and then the value sticks. I ran into a similar version of this bug later when adding username — the sidebar tried to read `username_locked` before the defaults dict had a chance to set it, which threw an `AttributeError`, and the fix was the same pattern: initialize early, before anything tries to read it.

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

The habit I'm definitely keeping is starting every feature in plan mode — writing out the design and getting sign-off before a single line of code gets written. It felt slow at first but it actually saved time because the agents had a clear spec to work against, and when something was wrong it was obvious whether it was a spec problem or an implementation problem. If I did this again, I'd also set up the `CLAUDE.md` config file on day one instead of partway through — once it was in place with defined branching rules, commit checkpoints, and the localhost verification step, the whole workflow became much more consistent. The biggest mindset shift for me is that AI-generated code isn't automatically correct just because it runs — I caught a real billing-message bug that only showed up during manual testing, not in any test suite, which reminded me that tests check contracts and humans check experience. Going forward I think of AI as a very fast junior developer: capable of producing a lot of code quickly, but still needs someone to review it and actually use it before shipping.

