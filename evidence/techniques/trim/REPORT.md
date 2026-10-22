# Kompactor A/B evidence

Real headless Claude Code sessions (`claude -p`, Claude Code 2.1.302 (Claude Code), model claude-sonnet-5-5), Kompactor 0.8.6 at level 3 (Balanced). 3 run(s) per task and condition; same prompt, tools, turn limit and budget cap in both conditions. Generated 2026-10-22.

**Total across 6 tasks: 540,407 › 500,720 tokens (-7%), cost $0.25 › $0.23 (-6%), output tokens +2%. Correct answers: 18/18 without, 18/18 with Kompactor.**

| Task | Lang | Tokens without (min–max) | Tokens with (min–max) | Δ tokens | Cost without | Cost with | Δ cost | Tool output chars | Turns | Correct |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| py-failing-tests | python | 67,326 (67k–67k) | 68,150 (68k–68k) | +1% | $0.038 | $0.038 | +1% | 3.2k › 4.1k | 2.0 › 2.0 | 3/3 › 3/3 |
| py-git-history | python | 117,066 (95k–130k) | 120,543 (96k–133k) | +3% | $0.045 | $0.053 | +18% | 1.6k › 4.2k | 3.7 › 3.7 | 3/3 › 3/3 |
| py-locate-code | python | 100,870 (101k–101k) | 112,712 (101k–136k) | +12% | $0.046 | $0.046 | -0% | 3.8k › 4.0k | 3.0 › 3.3 | 3/3 › 3/3 |
| go-locate-code | go | 99,764 (99k–101k) | 66,115 (66k–66k) | -34% | $0.040 | $0.029 | -28% | 2.2k › 0.5k | 3.0 › 2.0 | 3/3 › 3/3 |
| ts-locate-code | typescript | 88,457 (66k–100k) | 66,290 (66k–66k) | -25% | $0.039 | $0.031 | -20% | 0.6k › 0.3k | 2.7 › 2.0 | 3/3 › 3/3 |
| react-impact | react | 66,924 (67k–67k) | 66,911 (67k–67k) | -0% | $0.038 | $0.034 | -11% | 2.4k › 1.3k | 2.3 › 2.0 | 3/3 › 3/3 |

Tokens = input + cache writes + cache reads + output, summed over every API call in the session (what Claude Code bills). Δ is relative to the run without Kompactor. Correct means the final answer contained every expected fact (see `bench/tasks.json`).

## What happened in each run

Tool calls Claude made (from the session transcript), result size, and what Kompactor changed.

- **go-locate-code · baseline** (100,836 tokens, 3 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|func (176 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (4,291 chars)
- **go-locate-code · baseline** (99,234 tokens, 3 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|func (245 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (872 chars)
- **go-locate-code · baseline** (99,223 tokens, 3 turns): Grep func validateRequiredFlagGroups|func .*[Rr]equiredTogether|f (176 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (872 chars)
- **go-locate-code · kompactor** (66,184 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|requ (691 chars) · Kompactor: nothing to compact
- **go-locate-code · kompactor** (65,942 tokens, 2 turns): Grep func validateRequiredFlagGroups|func.*RequiredFlagGroups (186 chars) · Kompactor: nothing to compact
- **go-locate-code · kompactor** (66,219 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|Requ (563 chars) · Kompactor: nothing to compact
- **py-failing-tests · baseline** (67,120 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -60 (2,765 chars)
- **py-failing-tests · baseline** (67,415 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars)
- **py-failing-tests · baseline** (67,444 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars)
- **py-failing-tests · kompactor** (68,158 tokens, 2 turns): Bash .venv/bin/pytest tests -v (4,138 chars, compacted) · Kompactor: bash ×1 (−1,270 tokens)
- **py-failing-tests · kompactor** (68,135 tokens, 2 turns): Bash .venv/bin/pytest tests -v (4,138 chars, compacted) · Kompactor: bash ×1 (−1,270 tokens)
- **py-failing-tests · kompactor** (68,156 tokens, 2 turns): Bash .venv/bin/pytest tests -v (4,138 chars, compacted) · Kompactor: bash ×1 (−1,270 tokens)
- **py-git-history · baseline** (94,518 tokens, 3 turns): Bash git log -n 40 --format='@@%h' --name-only | awk '/^@@/{delet (189 chars); Bash git log -n 40 --name-only --format= | grep '^src/' | sort |  (122 chars)
- **py-git-history · baseline** (126,657 tokens, 4 turns): Bash git log -n 40 --format='C %H' --name-only | awk '/^C /{delet (189 chars); Bash git log -n 40 --format= --name-only -- src | sort | uniq -c  (120 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars)
- **py-git-history · baseline** (130,022 tokens, 4 turns): Bash git log -n 40 --format='C %h' --stat=200 | awk '/^C /{delete (206 chars); Bash git log -n 40 --format='C %h' --name-only -- src/ (1,702 chars); Bash git log -n 40 --format='C %h' --name-only (2,257 chars)
- **py-git-history · kompactor** (96,489 tokens, 3 turns): Bash git log -n 40 --format='C %H' --name-only | awk '/^C /{delet (189 chars); Bash git log -n 40 --format='C %h' --name-only (2,257 chars) · Kompactor: nothing to compact
- **py-git-history · kompactor** (131,674 tokens, 4 turns): Bash git log -n 40 --format='@@%h' --name-only | awk '/^@@/{delet (189 chars); Bash git log -n 40 --format='@@%h' --name-only -- src/ (1,702 chars); Bash git log -n 40 --format='@@%h' --name-only (2,257 chars) · Kompactor: nothing to compact
- **py-git-history · kompactor** (133,465 tokens, 4 turns): Bash git log -n 40 --name-only --pretty=format:'@@%h' | awk '/^@@ (189 chars); Bash git log -n 40 --stat --pretty=format:'@@%h' -- src/ (4,639 chars); Bash git log -n 40 --stat=200 --pretty=format:'@@%h' | grep -E '^ (1,187 chars) · Kompactor: nothing to compact
- **py-locate-code · baseline** (100,883 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (422 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,133 chars)
- **py-locate-code · baseline** (100,797 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars)
- **py-locate-code · baseline** (100,931 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|dumps\( (209 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (4,135 chars)
- **py-locate-code · kompactor** (101,217 tokens, 3 turns): Grep def save_session|URLSafeTimedSerializer|class SecureCookieSe (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars) · Kompactor: nothing to compact
- **py-locate-code · kompactor** (101,177 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars) · Kompactor: nothing to compact
- **py-locate-code · kompactor** (135,743 tokens, 4 turns): Grep def save_session|class SecureCookieSessionInterface|dumps\( (209 chars); Read  (491 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (4,076 chars) · Kompactor: nothing to compact
- **react-impact · baseline** (66,694 tokens, 2 turns): Grep createStore|vanilla (1,666 chars)
- **react-impact · baseline** (67,400 tokens, 3 turns): Grep createStore|vanilla (1,666 chars); Grep export (const|function) createStore|CreateStore (245 chars); Grep createStore|vanilla (1,666 chars); Grep export (const|function) createStore|CreateStore (245 chars)
- **react-impact · baseline** (66,677 tokens, 2 turns): Grep createStore|vanilla (1,666 chars)
- **react-impact · kompactor** (67,139 tokens, 2 turns): Grep createStore|vanilla (1,666 chars) · Kompactor: nothing to compact
- **react-impact · kompactor** (66,617 tokens, 2 turns): Grep createStore|from '\./vanilla|from "\./vanilla (665 chars) · Kompactor: nothing to compact
- **react-impact · kompactor** (66,977 tokens, 2 turns): Grep createStore|vanilla (1,666 chars) · Kompactor: nothing to compact
- **ts-locate-code · baseline** (99,635 tokens, 3 turns): Grep dedupingInterval (260 chars); Grep shouldStartNewRequest|FETCH\[ (580 chars)
- **ts-locate-code · baseline** (65,962 tokens, 2 turns): Grep dedupingInterval (260 chars)
- **ts-locate-code · baseline** (99,774 tokens, 3 turns): Grep dedupingInterval (260 chars); Grep shouldStartNewRequest|FETCH\[ (580 chars)
- **ts-locate-code · kompactor** (66,273 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact
- **ts-locate-code · kompactor** (66,291 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact
- **ts-locate-code · kompactor** (66,305 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact

## Answers

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test failed: 482 passed, 1 failed, 4 skipped.

**Failed:** `tests/test_helpers.py::TestStreaming::test_async_view`

**Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`

**Why:** The test defines an async view. Flask's `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref`, and the import fails because `asgiref` isn't installed in `.venv`. This is a missing optional dependency in the environment, not a code bug. Installing the async extra (`pip install asgiref`, or `pip install -e '.[async]'`) should fix it. I haven't run that, since you asked me not to change anything.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often were:

1. `src/flask/cli.py`: touched by 4 commits
2. `src/flask/app.py`: touched by 4 commits

The next most frequent files were `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each. I counted file appearances in `git log -n 40 --name-only`. A file can appear only once per commit, so each count is a commit count.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
**File:** `src/flask/sessions.py`

**Class:** `SecureCookieSessionInterface` (line 284)

**Method:** `save_session` (line 337). It serializes and signs the session on line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
response.set_cookie(name, val, expires=expires, httponly=httponly, ...)
```

- **Signing:** `get_signing_serializer` (line 303) builds the itsdangerous `URLSafeTimedSerializer`. It uses `app.secret_key` plus any `SECRET_KEY_FALLBACKS`, with the interface's `salt`, `key_derivation` and `digest_method`. The payload is encoded with `session_json_serializer` (Flask's tagged JSON serializer). If there is no secret key, it returns `None`.
- **Setting the cookie:** `save_session` then calls `response.set_cookie(...)` with the signed value.
- **Reading it back:** `open_session` (line 323) does the reverse. It calls `s.loads(val, max_age=...)` and returns an empty session on `BadSignature`.
- **Caller:** Flask's request-handling code calls `save_session` after the response is built. The session object itself is `SecureCookieSession`, a dict subclass in the same file.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: 1 failed, 482 passed, 4 skipped.

**Failure:** `tests/test_helpers.py::TestStreaming::test_async_view`
- **Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- **Why:** The test registers an `async def` view. Flask's `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync` and hits an `ImportError`. The `.venv` doesn't have `asgiref`, which comes with Flask's `async` extra. This is an environment problem, not a code bug. Installing it (`pip install asgiref` or `pip install -e ".[async]"`) should fix it.

**Skipped (4):** The three dotenv tests are `test_load_dotenv`, `test_dotenv_path` and `test_disable_dotenv_from_env`. They are skipped with "dotenv is not installed". I only saw those three skip lines, because Kompactor hid the other passing-test lines in the output. I didn't see which test is the fourth skip.

I didn't change any code.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
Flask creates and signs the session cookie in `src/flask/sessions.py`, in the class `SecureCookieSessionInterface`.

The method that serializes the session into the cookie is `save_session` (line 337). The signing happens at line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
```

- **Signing:** `get_signing_serializer` (line 303) builds an itsdangerous `URLSafeTimedSerializer`. It uses `app.secret_key`, plus any `SECRET_KEY_FALLBACKS`, together with the interface's salt, key derivation and digest method. `.dumps()` serializes the session dict and signs it.
- **Cookie:** `save_session` then passes the signed value to `response.set_cookie(...)` at line 374. It sets the expiry, `httponly`, `secure`, `samesite`, domain and path from the app config.
- **Reading it back:** `open_session` (line 323) is the reverse. It calls `s.loads(val, max_age=...)` and returns an empty session if the signature is bad.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often are tied at 4 commits each:

- **`src/flask/app.py`** was touched in 4 commits: `329c32b`, `d73fa1c`, `7203fea` and `81798b4`.
- **`src/flask/cli.py`** was touched in 4 commits: `7689f98`, `8285adf`, `36e4a82` and `954f568`.

The next most frequent files were `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each.

I used `git log --name-only`, which lists the same changed files as `--stat`. I counted by hand from that output because the awk one-liner was blocked.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails: 482 passed, 4 skipped, 1 failed. I didn't change any code.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- The key error is `RuntimeError: Install Flask with the 'async' extra in order to use async views.` It is raised at `src/flask/app.py:1096`, in `Flask.async_to_sync`.
- The cause is environmental. `async_to_sync` tries `from asgiref.sync import async_to_sync`, and that import fails with `ImportError` because `asgiref` isn't installed in `.venv`. The test defines an async view, so Flask needs `asgiref` to run it.
- Installing the `async` extra (`asgiref`) into the venv should fix it. This is a missing dependency, not a bug in Flask's code.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session` (line 337) serializes the session into the cookie.

`save_session` does the serializing and signing at line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
response.set_cookie(name, val, expires=expires, httponly=httponly, ...)
```

- **Signing:** `get_signing_serializer` (line 303) builds an itsdangerous `URLSafeTimedSerializer`. It is keyed with `app.secret_key` plus any `SECRET_KEY_FALLBACKS`. It also uses the interface's `salt`, `key_derivation` and `digest_method`. The payload is encoded with `session_json_serializer`, Flask's tagged JSON serializer.
- **Reading it back:** `open_session` (line 323) reverses this with `s.loads(val, max_age=...)`. A `BadSignature` error gives an empty session.
- **Cookie behavior:** `save_session` also deletes the cookie when a modified session is empty. It skips setting it when `should_set_cookie` says no, and it adds `Vary: Cookie` when the session was accessed.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits, with no path filter, the two `src/` files changed most often are:

1. `src/flask/cli.py` was touched in 4 commits.
2. `src/flask/app.py` was touched in 4 commits.

They tie at 4. The next files are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 each.

I counted each file once per commit. I used `git log -n 40 --name-only` instead of `--stat`, because it lists the same files per commit without the diffstat. I then filtered to `src/`.

I first ran it with `-- src`, which gave different numbers (11 for `app.py`, 10 for `sansio/app.py`). That was the wrong query. With a path filter, `-n 40` takes the 40 most recent commits that touch `src/`, not the 40 most recent overall.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: 1 failed, 482 passed, 4 skipped. I changed no code.

**Failure**
- `tests/test_helpers.py::TestStreaming::test_async_view` fails with `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- The error is raised at `src/flask/app.py:1096` in `Flask.async_to_sync`. That method tries `from asgiref.sync import async_to_sync`, and the import fails because `asgiref` isn't installed in `.venv`.
- This is an environment problem, not a code bug. Installing the async extra (`pip install asgiref`, or `pip install -e ".[async]"`) should fix it.

**Skipped**
- Three skipped tests are `tests/test_cli.py::test_load_dotenv`, `test_dotenv_path` and `test_disable_dotenv_from_env`. They are skipped because `python-dotenv` isn't installed.
- The output only named those three, so I don't know which test is the fourth skip or why. The compacted output hid it.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface` (line 284)
- **Method:** `save_session` (line 337)

`save_session` serializes and signs the session on line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
```

It then writes the result to the response with `response.set_cookie(...)` on line 374.

`get_signing_serializer` (line 303) builds the signer. It returns an itsdangerous `URLSafeTimedSerializer` keyed on `app.secret_key`, plus any `SECRET_KEY_FALLBACKS`. It also takes the salt, key derivation, digest method and JSON serializer from the interface. If no secret key is set, it returns `None`.

`dumps` on that serializer is what produces the signed, timestamped cookie value. `open_session` (line 323) is the reverse path: it reads the cookie and calls `s.loads(val, max_age=...)`.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
Result: 482 passed, 4 skipped, 1 failed. I changed no code.

**Failing test:** `tests/test_helpers.py::TestStreaming::test_async_view`

**Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`, raised at `src/flask/app.py:1096` in `async_to_sync`.

**Why:** The test defines an `async` view. Flask runs async views through `asgiref`, and `asgiref` isn't installed in `.venv`. The import fails, and Flask raises that `RuntimeError`. This is a missing optional dependency in the environment, not a bug in the code. Installing the async extra (`pip install "flask[async]"` or `pip install asgiref`) should make the test pass. I haven't run that.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often are tied at 4 commits each:

- **`src/flask/app.py`** was touched in 4 commits: `329c32b`, `d73fa1c`, `7203fea` and `81798b4`.
- **`src/flask/cli.py`** was touched in 4 commits: `7689f98`, `8285adf`, `36e4a82` and `954f568`.

The next closest files were `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each.

I ran `git log -n 40 --name-only` with no path filter, as you specified. The window runs from `d086db8` back to `91c6b3f`. Many of those 40 commits only changed tests, docs or CI, which is why the counts are low. I counted by reading the output, not with a script.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
**File:** `src/flask/sessions.py`

**Class:** `SecureCookieSessionInterface` (line 284), which is Flask's default session interface.

**Method:** `save_session(self, app, session, response)` (line 337) serializes the session into the cookie.

- **Signing:** line 373 calls `self.get_signing_serializer(app).dumps(dict(session))`. `get_signing_serializer` (line 303) builds an `itsdangerous.URLSafeTimedSerializer`. It uses `app.secret_key`, plus any `SECRET_KEY_FALLBACKS`. The salt is `"cookie-session"`. The key derivation is `hmac` and the digest is sha1. The payload is serialized with `session_json_serializer`, a compact JSON serializer.
- **Setting the cookie:** line 374 passes the resulting string to `response.set_cookie(...)`. The cookie options come from the `get_cookie_*` helpers.

`open_session` (line 323) does the reverse. It reads the cookie and verifies it with `s.loads(val, max_age=...)`.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test failed: 482 passed, 4 skipped, 1 failed. I changed no code.

**Failure**

- `tests/test_helpers.py::TestStreaming::test_async_view`
  - Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
  - Why: the test defines an `async def` view. `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync.async_to_sync`, and the import fails because `asgiref` isn't installed in `.venv`. So this is a missing optional dependency in the environment, not a bug in Flask. Installing the `async` extra (`pip install "flask[async]"` or `pip install asgiref`) should fix it.

**Skipped (4)**

- `tests/test_cli.py::test_load_dotenv`, `test_dotenv_path` and `test_disable_dotenv_from_env` were skipped with "dotenv is not installed".
- The fourth skipped test was in the part of the output that was cut, so I can't name it or say why it was skipped.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits (`git log -n 40`, no path filter), the two `src/` files changed most often are tied at 4 commits each:

1. `src/flask/app.py` was touched in 4 commits: `329c32b`, `d73fa1c`, `7203fea` and `81798b4`.
2. `src/flask/cli.py` was touched in 4 commits: `7689f98`, `8285adf`, `36e4a82` and `954f568`.

The next most frequent files were `src/flask/sansio/app.py` and `src/flask/helpers.py`, with 2 commits each. Every other `src/` file appeared in only 1.

I counted by hand from the `git log --name-only` output, because the one-line awk tally needed approval.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
The session cookie is created and signed in `SecureCookieSessionInterface.save_session` in `src/flask/sessions.py`.

- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, starting at line 284. It is the default session interface.
- **Method:** `save_session(self, app, session, response)`, starting at line 337.

Line 373 of `save_session` serializes and signs the session:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
```

It then passes `val` to `response.set_cookie(...)` on the lines that follow.

- **Signing:** `get_signing_serializer` (line 303) builds the `itsdangerous.URLSafeTimedSerializer`. It uses `app.secret_key`, plus any `SECRET_KEY_FALLBACKS`, with the salt `"cookie-session"`, HMAC key derivation and SHA-1. The payload is serialized with Flask's `session_json_serializer`, a compact JSON serializer that handles extra Python types such as datetime and tuple.
- **When no cookie is written:** `save_session` returns early without setting a cookie in two cases. One is an empty session that was never modified. The other is when `should_set_cookie` says no. If the session was modified to empty, it deletes the cookie instead.
- 
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The function is `validateRequiredFlagGroups`, at `flag_groups.go:144`.

It takes a map from each flag group to the set/unset status of its flags. For each group it collects the flags that aren't set. If every flag is unset, or none are, the group is fine. Otherwise it returns an error like `if any flags in the group [a b] are set they must all be set; missing [b]`.

`MarkFlagsRequiredTogether` (`flag_groups.go:33`) registers the groups. `ValidateFlagGroups` (`flag_groups.go:81`) calls `validateRequiredFlagGroups` at line 99, after `processFlagForGroupAnnotation` has built the status map.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
The function is `validateRequiredFlagGroups` in `flag_groups.go`, at line 144.

It takes the group-status map and returns an error if a group is only partly set. The groups come from the `requiredAsGroupAnnotation` annotation, which `MarkFlagsRequiredTogether` sets. The public `ValidateFlagGroups` (line 79) calls it.
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
`useSWR` avoids duplicate requests with the **`dedupingInterval`** config option. Its default is **2000 ms (2 seconds)**, set in `src/_internal/utils/config.ts:76` (`dedupingInterval: 2 * 1000`).

The mechanism is in `src/index/use-swr.ts`:
- A shared `FETCH` map holds the in-flight request for each key. It stores `[promise, startTimestamp]`.
- At line 515, `shouldStartNewRequest = !FETCH[key] || !opts.dedupe`. If a request for that key is already in flight and dedupe is on, no new fetcher call is made. The hook reuses the existing promise (`[newData, startAt] = FETCH[key]` at line 599).
- When a request finishes, line 606 runs `setTimeout(cleanupState, config.dedupingInterval)`. The `FETCH` entry stays for the deduping interval, so identical calls from other components in that window are still deduplicated.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
Within the 40 most recent commits (no path filter), the two `src/` files changed most often are tied at 4 commits each:

| File | Commits touching it |
|---|---|
| `src/flask/app.py` | 4 (`329c32b`, `d73fa1c`, `7203fea`, `81798b4`) |
| `src/flask/cli.py` | 4 (`7689f98`, `8285adf`, `36e4a82`, `954f568`) |

The next most-changed files are `src/flask/sansio/app.py` (`d086db8`, `9368fb3`) and `src/flask/helpers.py` (`7689f98`, `d318b68`), with 2 commits each.

Most of those 40 commits didn't touch `src/` at all. I excluded `examples/celery/src/...`, which isn't under the top-level `src/`.
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
`useSWR` avoids duplicate requests with the **`dedupingInterval`** config option. Its default is **2000 ms** (`2 * 1000`), set at `src/_internal/utils/config.ts:76`. The option is typed in `src/_internal/types.ts:224`.

How it works: when a request starts, SWR records it in an in-flight request map (`FETCH`) under the key. Calls with the same key that arrive within `dedupingInterval` reuse that promise instead of starting a new request. The entry is cleared after the interval, via the `setTimeout(cleanupState, config.dedupingInterval)` at `src/index/use-swr.ts:606`.

I only searched for `dedupingInterval`. The in-flight map and the reuse logic come from my general knowledge of SWR, and I didn't open the code to check them.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The function is `validateRequiredFlagGroups`, in `flag_groups.go:144`.

For each flag group, it collects the flags that are unset. It skips the group if none are unset (all set) or if all are unset (none set). Otherwise it returns an error: `if any flags in the group [...] are set they must all be set; missing [...]`.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore` directly, so those are the ones a signature change would break:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside `create`.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.

**Probably unaffected:**
- **`src/index.ts`** only does `export * from './vanilla.ts'`, so it re-exports whatever the new signature is.
- **The middleware files** (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) import `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts`, not `createStore`. Several also augment the module with `declare module '../vanilla'`. These only break if your change touches those shared types or the `StoreMutators` interface.

If you also change the `CreateStore` type or its generics, `react.ts` and `traditional.ts` import types from `vanilla.ts`, so check their type imports too. Files outside `src/`, such as tests and docs, may call `createStore` as well. I only searched `src/`.
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
`useSWR` avoids duplicate requests with the **`dedupingInterval`** option. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`.

The mechanism is in `src/index/use-swr.ts`. When a request starts, SWR stores the in-flight promise in a shared `FETCH` cache entry, keyed by the SWR key. Any other hook using the same key during that window reuses the stored promise instead of calling the fetcher again. Around line 606, a `setTimeout` clears that entry after `config.dedupingInterval` has passed. Until then, further calls for that key count as duplicates.

I only grepped for the option name. I didn't read the surrounding code in `use-swr.ts`, so the description of the `FETCH` entry comes from my knowledge of SWR, not from this checkout.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
It's `validateRequiredFlagGroups`, in `flag_groups.go:144`.

It covers flags grouped with `MarkFlagsRequiredTogether`. If any flag in a group is set, it returns an error naming the flags that are still missing. `validateOneRequiredFlagGroups`, just below it at line 167, is a different check: it requires at least one flag from a group to be set.

I found it by searching for the function name and didn't open the function body.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Only two files under `src/` call `createStore`, so those are the ones a signature change would break:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside `create`.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.

Other files under `src/` that touch `vanilla.ts` probably wouldn't need changes:

- **`src/index.ts`** does `export * from './vanilla.ts'`, so it re-exports the new signature automatically.
- **The middleware files** import only types, such as `StateCreator` and `StoreMutatorIdentifier`. The files are `combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe` and `subscribeWithSelector`. Several of them also use `declare module '../vanilla'` to augment the mutator types. They need edits only if your change touches `StateCreator`, `StoreMutatorIdentifier`, or the `CreateStore` type they augment.
- **`src/react/shallow.ts` and `src/shallow.ts`** use `vanilla/shallow.ts`, which has nothing to do with `createStore`.

Two things to watch for beyond the call sites:

- `createStore` is curried. `createStore(fn)` returns a store, and `createStore()` returns `createStoreImpl`, as the check at `vanilla.t
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The function is `validateRequiredFlagGroups`, at `flag_groups.go:144`.

It takes a map from each flag group to its flags' set/unset status. For each group it collects the unset flags. If none are unset or all are unset, the group passes. If only some are unset, it returns this error: `if any flags in the group [...] are set they must all be set; missing [...]`.

Groups are registered with `MarkFlagsRequiredTogether` (`flag_groups.go:33`).
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
`useSWR` deduplicates requests with the **`dedupingInterval`** option. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`.

While a request for a key is in flight, or finished less than `dedupingInterval` ago, other `useSWR` calls with the same key reuse that request. They don't start a new fetch.

The mechanism is in `src/index/use-swr.ts`, where line 606 uses the option:

```ts
setTimeout(cleanupState, config.dedupingInterval)
```

This schedules the cleanup of the in-flight request record. The record stays until the interval has passed, and that is how the dedup window is enforced.

I only searched for the option name. I didn't read the surrounding logic in `use-swr.ts`, so I haven't confirmed how the in-flight record is looked up.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
The function is `validateRequiredFlagGroups`, in `flag_groups.go` at line 144. It takes a map of flag groups to flag-set status and returns an error if a group is only partly set.

`Command.MarkFlagsRequiredTogether` is in the same file at line 33. It marks flags as a required-together group, and `validateRequiredFlagGroups` enforces that marking.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore` directly, so those are the ones a signature change would break:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside the `create` implementation.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.

Whether they need edits depends on the change:

- **Parameters or return type:** both call sites would need updating. They also pass the result through to hooks, so any change to the returned `StoreApi` type could ripple further.
- **The curried form (`createStore<T>()(...)`):** this form is handled by the `CreateStore` type (line 43) and `createStoreImpl` (line 60) in `vanilla.ts` itself. Changing it affects the callers' typings but not their code.

Other files only touch `vanilla.ts` types, not `createStore`:

- **`src/index.ts`** re-exports everything with `export * from './vanilla.ts'`. It needs no edit, but its public API changes.
- **The middleware files** import only types such as `StateCreator` and `StoreMutatorIdentifier`. They would change only if you alter those types. These are `combine.ts`, `redux.ts`, `persist.ts`, `immer.ts`, `devtools.ts`, `ssrSafe.ts` a
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
SWR deduplicates through a shared in-flight request cache, and the config option that controls it is **`dedupingInterval`**.

**How it works** (`src/index/use-swr.ts`, around lines 515–606):
- Every in-flight request is stored in a global `FETCH` map, keyed by the SWR key. Each entry holds the fetch promise and its start timestamp.
- When a fetch is triggered with `opts.dedupe` set, as on mount, focus and reconnect revalidations, it checks `shouldStartNewRequest = !FETCH[key] || !opts.dedupe` (line 515).
- If `FETCH[key]` already exists, no new request starts. The hook reuses the existing promise with `[newData, startAt] = FETCH[key]` (line 599).
- A request that actually starts writes `FETCH[key] = [fetcher(...), getTimestamp()]` (line 586).
- After the request settles, the entry isn't removed immediately. A `setTimeout(cleanupState, config.dedupingInterval)` (line 606) keeps it in `FETCH` for the interval. Calls to the same key inside that window therefore share the result, even if the first request has already finished.

**Default value:** `dedupingInterval: 2 * 1000` (2 seconds), set in `src/_internal/utils/config.ts:76`. Its type is declared in `src/_internal/types.ts:224`.
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
`useSWR` avoids duplicate requests with the **`dedupingInterval`** option.

- **Default value:** it is set to `2 * 1000` (2 seconds) at `src/_internal/utils/config.ts:76`.
- **Where it takes effect:** in `src/index/use-swr.ts`, when a request starts, the in-flight promise is stored in a shared cache keyed by the SWR key. While that entry exists, other hooks using the same key reuse the promise instead of calling the fetcher again. At line 606, a `setTimeout(cleanupState, config.dedupingInterval)` clears that entry after the interval. The interval is therefore how long a request counts as in flight, and it also covers a short window after the request finishes.

I only grepped for `dedupingInterval`. The description of the shared in-flight cache comes from my knowledge of SWR, not from reading that part of `use-swr.ts`.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Changing the `createStore` signature would directly affect two files under `src/`, and a third only if you change the exported types:

- **`src/react.ts`**: imports `createStore` and calls `createStore(createState)` at line 54, inside `create`.
- **`src/traditional.ts`**: imports `createStore` and calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.
- **`src/index.ts`** (conditional): it only does `export * from './vanilla.ts'`. It needs no edit, but the new signature becomes public API through it.

Nothing else under `src/` calls `createStore`. That includes `src/middleware/*` and `src/vanilla/*`, and `src/shallow.ts` only re-exports `shallow`.

If the change goes through the `CreateStore` or `CreateStoreImpl` types in `vanilla.ts`, the files that import types from `./vanilla.ts` could also see compile errors. `react.ts` and `traditional.ts` both do, at lines 9 and 10.

I only searched `src/`. Tests, docs and type-test files outside `src/` may also call `createStore`.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore` directly, so those are the ones a signature change would break:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside `create`.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.

`src/index.ts` only does `export * from './vanilla.ts'`. It re-exports the new signature and needs no edit.

The middleware files in `src/middleware/` (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe` and `subscribeWithSelector`) don't call `createStore`. They import the `StateCreator` and `StoreMutatorIdentifier` types from `vanilla.ts`. Several of them also augment the module with `declare module '../vanilla'`. If your change only touches the `createStore` or `CreateStore` type, none of them need edits. They would only be affected if you also changed `StateCreator`, `StoreApi`, or the mutator types.

This search covered `src/` only. Tests and docs that call `createStore` sit outside it and may need updating too.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Only two files under `src/` call `createStore` directly, so they are the ones a signature change would break:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside `create`.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.

`src/index.ts` only does `export * from './vanilla.ts'`. It re-exports the new signature, so it needs no edit.

The middleware files in `src/middleware/` don't call `createStore`. They import types such as `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts`, and several use `declare module '../vanilla'` augmentations. They would only need changes if you also changed those types, for example the `CreateStore` type or the `StateCreator` shape, and not just the `createStore` parameters.

This is based on a text search for `createStore` and `vanilla` under `src/`. I haven't type-checked it, so run `tsc` after the change to confirm. Tests and docs outside `src/` may also call `createStore`, and I didn't look there.
```
</details>
