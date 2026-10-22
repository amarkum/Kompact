# Kompactor A/B evidence

Real headless Claude Code sessions (`claude -p`, Claude Code 2.1.302 (Claude Code), model claude-sonnet-5-5), Kompactor 0.8.6 at level 3 (Balanced). 3 run(s) per task and condition; same prompt, tools, turn limit and budget cap in both conditions. Generated 2026-10-22.

**Total across 6 tasks: 471,301 › 475,582 tokens (+1%), cost $0.20 › $0.21 (+4%), output tokens +2%. Correct answers: 18/18 without, 18/18 with Kompactor.**

| Task | Lang | Tokens without (min–max) | Tokens with (min–max) | Δ tokens | Cost without | Cost with | Δ cost | Tool output chars | Turns | Correct |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| py-failing-tests | python | 67,353 (67k–68k) | 67,808 (68k–68k) | +1% | $0.035 | $0.035 | +2% | 3.2k › 3.2k | 2.0 › 2.0 | 3/3 › 3/3 |
| py-locate-code | python | 77,688 (66k–101k) | 101,437 (101k–102k) | +31% | $0.034 | $0.043 | +24% | 1.5k › 3.6k | 2.3 › 3.0 | 3/3 › 3/3 |
| py-git-history | python | 115,882 (95k–127k) | 106,137 (95k–128k) | -8% | $0.038 | $0.038 | -0% | 0.4k › 0.4k | 3.7 › 3.3 | 3/3 › 3/3 |
| go-locate-code | go | 65,982 (66k–66k) | 66,508 (66k–67k) | +1% | $0.029 | $0.031 | +4% | 0.7k › 0.9k | 2.0 › 2.3 | 3/3 › 3/3 |
| ts-locate-code | typescript | 65,935 (66k–66k) | 66,427 (66k–66k) | +1% | $0.030 | $0.031 | +4% | 0.3k › 0.3k | 2.0 › 2.0 | 3/3 › 3/3 |
| react-impact | react | 78,462 (67k–100k) | 67,264 (67k–67k) | -14% | $0.039 | $0.036 | -8% | 2.5k › 1.7k | 2.3 › 2.0 | 3/3 › 3/3 |

Tokens = input + cache writes + cache reads + output, summed over every API call in the session (what Claude Code bills). Δ is relative to the run without Kompactor. Correct means the final answer contained every expected fact (see `bench/tasks.json`).

## What happened in each run

Tool calls Claude made (from the session transcript), result size, and what Kompactor changed.

- **go-locate-code · baseline** (65,977 tokens, 2 turns): Grep func validateRequiredFlagGroups|func .*RequiredTogether|requ (776 chars)
- **go-locate-code · baseline** (65,941 tokens, 2 turns): Grep func validateRequiredFlagGroups|func.*RequiredTogether|requi (652 chars)
- **go-locate-code · baseline** (66,028 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|func (776 chars)
- **go-locate-code · kompactor** (66,374 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|Requ (652 chars) · Kompactor: nothing to compact
- **go-locate-code · kompactor** (66,471 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|requ (691 chars) · Kompactor: nothing to compact
- **go-locate-code · kompactor** (66,679 tokens, 3 turns): Grep func validateRequiredFlagGroups (91 chars); Grep requiredAsGroup (599 chars); Grep func validateRequiredFlagGroups (91 chars); Grep requiredAsGroup (599 chars) · Kompactor: nothing to compact
- **py-failing-tests · baseline** (67,061 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -60 (2,765 chars)
- **py-failing-tests · baseline** (67,477 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars)
- **py-failing-tests · baseline** (67,520 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars)
- **py-failing-tests · kompactor** (67,608 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -60 (2,765 chars) · Kompactor: nothing to compact
- **py-failing-tests · kompactor** (67,931 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars) · Kompactor: nothing to compact
- **py-failing-tests · kompactor** (67,885 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars) · Kompactor: nothing to compact
- **py-git-history · baseline** (126,719 tokens, 4 turns): Bash git log -n 40 --format='C %h' --stat=200 | awk '/^C /{delete (205 chars); Bash git log -n 40 --format= --name-only -- src/ | sort | uniq -c (120 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars)
- **py-git-history · baseline** (94,504 tokens, 3 turns): Bash git log -n 40 --name-only --format='commit %h' -- | awk '/^c (194 chars); Bash git log -n 40 --name-only --format= | grep '^src/' | sort |  (122 chars)
- **py-git-history · baseline** (126,422 tokens, 4 turns): Bash git log -n 40 --format='C %h' --stat=200 | awk '/^C /{next}  (172 chars); Bash git log -n 40 --format= --name-only -- src/ | sort | uniq -c (120 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars)
- **py-git-history · kompactor** (127,590 tokens, 4 turns): Bash git log -n 40 --name-only --format='C %h' | awk '/^C /{delet (189 chars); Bash git log -n 40 --name-only --format= -- src/ | sort | uniq -c (120 chars); Bash git log -n 40 --name-only --format= | grep '^src/' | sort |  (122 chars) · Kompactor: nothing to compact
- **py-git-history · kompactor** (95,379 tokens, 3 turns): Bash git log -n 40 --format='@@%h' --name-only | awk '/^@@/{delet (189 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars) · Kompactor: nothing to compact
- **py-git-history · kompactor** (95,443 tokens, 3 turns): Bash git log -n 40 --name-only --format='C %h' | awk '/^C /{delet (189 chars); Bash git log -n 40 --name-only --format= | grep '^src/' | sort |  (122 chars) · Kompactor: nothing to compact
- **py-locate-code · baseline** (100,823 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars)
- **py-locate-code · baseline** (66,133 tokens, 2 turns): Grep def save_session|class SecureCookieSessionInterface|get_sign (477 chars)
- **py-locate-code · baseline** (66,107 tokens, 2 turns): Grep def save_session|class SecureCookieSessionInterface|get_sign (477 chars)
- **py-locate-code · kompactor** (101,383 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars) · Kompactor: nothing to compact
- **py-locate-code · kompactor** (101,403 tokens, 3 turns): Grep def save_session|URLSafeTimedSerializer|class SecureCookieSe (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,281 chars) · Kompactor: nothing to compact
- **py-locate-code · kompactor** (101,526 tokens, 3 turns): Grep def save_session|URLSafeTimedSerializer|class SecureCookieSe (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars) · Kompactor: nothing to compact
- **react-impact · baseline** (100,485 tokens, 3 turns): Grep createStore|from '(\./)?vanilla|from "\./vanilla (665 chars); Grep vanilla\.ts' (622 chars)
- **react-impact · baseline** (68,226 tokens, 2 turns): Grep createStore|StateCreator|vanilla (4,401 chars)
- **react-impact · baseline** (66,676 tokens, 2 turns): Grep createStore|vanilla (1,666 chars)
- **react-impact · kompactor** (67,254 tokens, 2 turns): Grep createStore|vanilla (1,666 chars) · Kompactor: nothing to compact
- **react-impact · kompactor** (67,260 tokens, 2 turns): Grep createStore|vanilla (1,666 chars) · Kompactor: nothing to compact
- **react-impact · kompactor** (67,279 tokens, 2 turns): Grep createStore|from '\./vanilla|from "\./vanilla|vanilla (1,666 chars) · Kompactor: nothing to compact
- **ts-locate-code · baseline** (65,873 tokens, 2 turns): Grep dedupingInterval (260 chars)
- **ts-locate-code · baseline** (65,937 tokens, 2 turns): Grep dedupingInterval (260 chars)
- **ts-locate-code · baseline** (65,995 tokens, 2 turns): Grep dedupingInterval (260 chars)
- **ts-locate-code · kompactor** (66,428 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact
- **ts-locate-code · kompactor** (66,409 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact
- **ts-locate-code · kompactor** (66,445 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact

## Answers

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails: 482 passed, 4 skipped, 1 failed. I didn't change any code.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- **Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- **Why:** The test defines an async view. `Flask.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync.async_to_sync` and hits an `ImportError`. That means `asgiref` isn't installed in `.venv`. It's an environment problem, not a code bug. Installing the async extra (`pip install asgiref`, or `pip install -e ".[async]"`) should fix it.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
**File:** `src/flask/sessions.py`

**Class:** `SecureCookieSessionInterface`, which starts at line 284.

**Method:** `SecureCookieSessionInterface.save_session` (line 337). It serializes and signs the session on line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
response.set_cookie(name, val, expires=expires, httponly=httponly, ...)
```

- **Signing:** `get_signing_serializer` (line 303) builds an `itsdangerous.URLSafeTimedSerializer`. It uses `app.secret_key`, with any `SECRET_KEY_FALLBACKS` listed before it. It also uses the interface's `salt`, its JSON `serializer` (`session_json_serializer`), and the key-derivation and digest settings. `.dumps()` serializes the session dict to JSON, adds a timestamp and signs it. The result is the cookie value.
- **Setting the cookie:** `save_session` then calls `response.set_cookie(...)` with the domain, path, secure, samesite, httponly and expiry settings.
- **Reading it back:** `open_session` (line 323) does the reverse. It calls `s.loads(val, max_age=...)` and returns an empty session if it raises `BadSignature`.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits with no path filter, the two `src/` files changed most often are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They are tied at 4. The next closest are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each.

I counted file names from `git log -n 40 --name-only` rather than reading the `--stat` output. A file appears once per commit in that list, so each count is a number of commits.

My first attempt used `-- src/` as a path filter. That takes the 40 most recent commits that touched `src/`, not the 40 most recent overall, so it gave different counts and I discarded it.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: 482 passed, 4 skipped, 1 failed. I didn't change any code.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Why: the test defines an `async def` view. Flask's `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync`, and that import fails. `asgiref` isn't installed in `.venv`, so the failure comes from the environment and not from a code bug.
- To fix it, you could install the extra with `.venv/bin/pip install asgiref` or `pip install -e '.[async]'`. I haven't done that.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`
- **Method:** `save_session` (line 337)

In `save_session`, line 373 does the serializing and signing. It calls `self.get_signing_serializer(app).dumps(dict(session))`. `response.set_cookie(...)` then writes the resulting value into the cookie.

`get_signing_serializer` (line 303) builds the signer, an itsdangerous `URLSafeTimedSerializer`. It uses `app.secret_key`, with any `SECRET_KEY_FALLBACKS` listed first and the current key last. It also applies the class's salt, JSON serializer, key derivation and digest method.

The reverse direction is `open_session` (line 323), which calls `s.loads(val, max_age=...)` and returns an empty session if the signature is bad.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often were:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They are tied at 4. Next come `src/flask/sansio/app.py` and `src/flask/helpers.py`, with 2 each.

I used `git log -n 40 --name-only` rather than `--stat`, with no path filter, and counted the `src/` lines. `--name-only` lists the same files as `--stat` and is easier to count. Each file appears at most once per commit, so the counts equal the number of commits that touched it.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test failed: 482 passed, 4 skipped, 1 failed. I changed no code.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Why: the test serves an `async def` view. `Flask.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync`, and the import fails. `asgiref` isn't installed in `.venv`, so this is a missing optional dependency, not a bug in Flask.
- Fix, if you want it: install the async extra, for example `.venv/bin/pip install asgiref`.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
Flask serializes and signs the session cookie in `src/flask/sessions.py`.

- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session`, at line 337. It serializes the session into the cookie value on line 373:
  ```python
  val = self.get_signing_serializer(app).dumps(dict(session))
  ```
- **Signing:** `get_signing_serializer` (line 303) builds the `URLSafeTimedSerializer`. It is keyed on the app's secret key, so `dumps()` both serializes the session dict and signs it. `save_session` then sets that value as the cookie with `response.set_cookie(...)`.

Loading goes the other way. `open_session` (around line 324) calls the same serializer to verify and deserialize the cookie.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They tie at 4. The next most frequent are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 each.

I counted with `git log -n 40 --name-only`, which lists each file once per commit. Merge commits show no files by default, so they don't add to any count.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: 482 passed, 4 skipped, 1 failed.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Why: the test defines an `async` view. Flask's `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync`, and that import fails. `asgiref` isn't installed in `.venv`, so the test fails. This is an environment problem, not a code bug.
- Fix, if you want it: install the extra with `.venv/bin/pip install asgiref`, or `pip install -e '.[async]'`. I didn't change anything.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session` (line 337).

On line 373, `save_session` runs `self.get_signing_serializer(app).dumps(dict(session))`. That call serializes the session dict and signs it. `response.set_cookie(...)` then writes the result as the cookie value.

`get_signing_serializer` (line 303) builds the signer. It returns an `itsdangerous.URLSafeTimedSerializer` created from:
- `app.secret_key`, with any `SECRET_KEY_FALLBACKS` placed before it;
- the interface's `salt`, `serializer` (Flask's tagged JSON serializer), `key_derivation` and `digest_method`.

`open_session` (line 323) is the reverse path. It calls `s.loads(val, max_age=...)` to verify the signature and rebuild the session.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often were:

1. `src/flask/cli.py`, touched by 4 commits
2. `src/flask/app.py`, touched by 4 commits

The next most frequent were `src/flask/sansio/app.py` and `src/flask/helpers.py`, with 2 commits each.

I listed the files changed per commit with `git log -n 40 --name-only`, kept the `src/` paths, and counted them. A file appears at most once per commit in that output, so each count is a commit count.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails: `tests/test_helpers.py::TestStreaming::test_async_view`. The run finished with 1 failed, 482 passed and 4 skipped.

**Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.` It is raised at `src/flask/app.py:1096`, in `Flask.async_to_sync`.

**Why:** The test defines an `async def` view. Flask runs async views through `asgiref`, and `async_to_sync` raises this error when `asgiref` can't be imported. The `.venv` doesn't have `asgiref`, which is the optional `async` extra. The failure comes from the environment, not from a code bug.

Installing the extra (`pip install "flask[async]"` or `pip install asgiref`) should fix it. I didn't change anything, as you asked.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session` (line 337) serializes the session into the cookie and sets it on the response.

`save_session` calls `self.get_signing_serializer(app).dumps(dict(session))` at line 373. That call produces the signed cookie value.

`get_signing_serializer` (line 303) builds the signer, an itsdangerous `URLSafeTimedSerializer`. It's keyed on `app.secret_key`. `open_session` (around line 324) uses the same serializer to load the cookie.

The base `SessionInterface.save_session` at line 263 is only the abstract hook.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails, 482 pass, and 4 are skipped.

**Failed:** `tests/test_helpers.py::TestStreaming::test_async_view`

**Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`

**Why:** The test calls an async view, and `Flask.async_to_sync` (`src/flask/app.py:1096`) needs `asgiref`. The `.venv` doesn't have it installed, so the import fails. The cause is the environment, not a code bug. Installing the `async` extra, for example `pip install asgiref`, should fix it. I didn't change anything.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits (no path filter), the two files under `src/` touched by the most commits are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They are tied at 4. The next closest are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 each, so those two are clearly the top pair.

I counted each file once per commit using `git log -n 40 --format= --name-only`, filtered to paths starting with `src/`. My first attempt limited the log to `src/`, which picked a different set of 40 commits, so I discarded it.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session()`, at line 337.

`save_session()` serializes and signs the session on line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
```

It then writes the result to the response with `response.set_cookie(name, val, ...)`.

The signing happens in `get_signing_serializer()` (line 303). It builds an `itsdangerous.URLSafeTimedSerializer` from these parts:
- **Keys:** `app.secret_key`, plus any `SECRET_KEY_FALLBACKS`.
- **Salt:** the interface's `salt` attribute.
- **Serializer:** `session_json_serializer`, which is Flask's tagged-JSON serializer.
- **Signer settings:** the key derivation and digest method.

`dumps()` on that serializer produces the signed, timestamped, URL-safe string that becomes the cookie value. If no secret key is set, `get_signing_serializer()` returns `None`.

The reverse path is `open_session()` (line 323). It calls `loads()` with a `max_age` taken from `permanent_session_lifetime`.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The check is done by `validateRequiredFlagGroups` in `flag_groups.go`, at line 144. It takes a map of group name to per-flag "is set" status. It returns an error if a group has some flags set but not all of them.

`ValidateFlagGroups` in the same file (line 79) is the public entry point. It collects the group status for the `requiredAsGroupAnnotation` annotation and then calls this function. The annotation is set by `MarkFlagsRequiredTogether`.
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
`useSWR` dedupes through the **`dedupingInterval`** option. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`.

Within that window, calls with the same key share one in-flight request instead of each firing their own. In `src/index/use-swr.ts`, around line 606, a `setTimeout(cleanupState, config.dedupingInterval)` clears the in-flight entry once the interval has passed. I only grepped for the option and didn't read the surrounding logic, so I haven't checked how the shared request is stored or looked up.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
Of the 40 most recent commits, the two `src/` files changed most often are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They are tied at 4. The next most-changed files are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 each.

I counted with `git log -n 40 --name-only`, keeping only paths that start with `src/`. A file is listed at most once per commit, so each count is a number of commits.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
The function is `validateRequiredFlagGroups`, at `flag_groups.go:144`.

It takes a map of flag groups to their set/unset state. It returns an error if a "required together" group has only some of its flags set. The public entry point that marks flags this way is `Command.MarkFlagsRequiredTogether`, at `flag_groups.go:33`.
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
The config option is **`dedupingInterval`**. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`. The option is typed in `src/_internal/types.ts:224`.

In `src/index/use-swr.ts`, the first call for a key stores its in-flight promise in a shared cache. Other `useSWR` calls for the same key within the interval reuse that promise instead of sending a new request. Around line 606, `setTimeout(cleanupState, config.dedupingInterval)` clears the stored request once the interval has passed, so a later call can fetch again.

I only grepped for `dedupingInterval`. I haven't read the rest of `use-swr.ts`, so the in-flight promise cache is from my recollection of SWR's design, not something I checked in this repo.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
`validateRequiredFlagGroups` in `flag_groups.go` (line 144) does this check. It takes the map of flag groups and returns an error unless every flag in a group is set or none are.

`MarkFlagsRequiredTogether` in the same file (line 33) is the public method that marks flags as a group.

I didn't read the function body. I identified it from its name and its position in the file.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore` directly, so they're the ones most likely to need changes:

- **`src/react.ts:54`** calls `createStore(createState)` inside `create`'s implementation.
- **`src/traditional.ts:70`** calls `createStore(createState)` inside `createWithEqualityFn`'s implementation.

Both files also import types from `./vanilla.ts` (lines 9 and 10 respectively). Those imports only matter if you change exported types such as `StoreApi` or `StateCreator`, not just the `createStore` signature.

**Probably unaffected, but worth a type-check:**
- **`src/index.ts`** only does `export * from './vanilla.ts'`. The public re-export updates itself.
- **`src/middleware/*.ts`** (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) only import types (`StateCreator`, `StoreMutatorIdentifier`, etc.) and never call `createStore`. They would need changes only if you alter those types.

If the change affects the `CreateStore` type or the curried form (`createStore()(...)`), also look at `createStoreImpl` and the cast at `src/vanilla.ts:60` and `src/vanilla.ts:99`. I checked `src/` only, so tests, docs and other directories that call `createS
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
`useSWR` avoids duplicate requests through the **`dedupingInterval`** option. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`.

When a request starts for a key, SWR records it in a shared in-flight map (`FETCH`). It clears that entry with `setTimeout(cleanupState, config.dedupingInterval)` (`src/index/use-swr.ts:606`). Other `useSWR` calls with the same key inside that window reuse the in-flight promise instead of calling the fetcher again.

I only grepped for `dedupingInterval`. I didn't read the surrounding fetch code, so the description of the in-flight map comes from my knowledge of SWR, not from this repo.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
The function is `validateRequiredFlagGroups`, defined at `flag_groups.go:144`.

It is called from `ValidateFlagGroups` (also in `flag_groups.go`), which collects the groups from the `cobra_annotation_required_if_others_set` annotation. That annotation is set by `MarkFlagsRequiredTogether`.

I only read the grep matches, not the function body, so I haven't confirmed the all-or-none logic myself.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The check is done by `validateRequiredFlagGroups` in `flag_groups.go:144`. It takes the map of group status data and returns an error if a group has some of its flags set but not all of them.

`MarkFlagsRequiredTogether` (line 33) registers the groups. `ValidateFlagGroups` (line 79) is the public entry point that calls the validator, along with the mutually-exclusive and one-required checks.
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
`useSWR` dedupes through the **`dedupingInterval`** option. Its default is **2000 ms** (`2 * 1000`), set at `src/_internal/utils/config.ts:76`. The type is declared in `src/_internal/types.ts:224`.

When a request starts, SWR records it in a shared in-flight map keyed by the cache key. Any other `useSWR` call for the same key within that window reuses the existing promise instead of fetching again. The cleanup that ends the window is scheduled with `setTimeout(cleanupState, config.dedupingInterval)` at `src/index/use-swr.ts:606`. I only grepped for the option name, so I haven't read the surrounding code that does the reuse.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Files under `src/` that call `createStore` directly, so they would need to change if the signature changes:

- **`src/react.ts`**: line 54, `createStore(createState)` inside `create`.
- **`src/traditional.ts`**: line 70, `createStore(createState)` inside `createWithEqualityFn`.

`src/index.ts` only re-exports with `export * from './vanilla.ts'`. It needs no edit, but the public API changes through it.

Files that don't call `createStore` but import other types from `vanilla.ts` (`StateCreator`, `StoreMutatorIdentifier`, and so on):
- `src/middleware/combine.ts`
- `src/middleware/redux.ts`
- `src/middleware/persist.ts`
- `src/middleware/immer.ts`
- `src/middleware/devtools.ts`
- `src/middleware/ssrSafe.ts`
- `src/middleware/subscribeWithSelector.ts`

These are only affected if the change touches those shared types. Several of them also use `declare module '../vanilla'` augmentations, which depend on `vanilla.ts` types such as `StoreMutators`.

The `CreateStore` type and the curried form (`createState ? createStoreImpl(createState) : createStoreImpl`) are both inside `vanilla.ts` itself.

I only searched `src/`. Tests, docs and other directories may also reference `createStore`.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
The function is `validateRequiredFlagGroups`, at `flag_groups.go:144`. It takes a `map[string]map[string]bool` of group status and returns an error if a group is only partly set.

The groups are registered by `MarkFlagsRequiredTogether` (`flag_groups.go:40`), which stores them under the `cobra_annotation_required_if_others_set` annotation. `ValidateFlagGroups` (`flag_groups.go:79`) calls `validateRequiredFlagGroups` as one of its checks.

I located the function by grep and did not read its body.
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
**Config option:** `dedupingInterval`. Its default is `2 * 1000` (2 seconds).

**Where the default is set:** `src/_internal/utils/config.ts:76`, in the default config object.

**How it works:** In `src/index/use-swr.ts`, a fetch for a key is recorded in a shared in-flight cache as `FETCH[key]`, together with its promise and a timestamp. If another `useSWR` hook asks for the same key and `dedupingInterval` hasn't expired, it reuses that in-flight promise instead of starting a new request.

The expiry is handled at `src/index/use-swr.ts:606`. After the request finishes, `setTimeout(cleanupState, config.dedupingInterval)` clears the entry. Until then, the same key is deduplicated.

I only grepped for `dedupingInterval`. The description of the `FETCH[key]` mechanism comes from my knowledge of SWR, not from reading that code here.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore` directly, so only they would need to change:

1. **`src/react.ts`**: `createImpl` calls `createStore(createState)` at line 54.
2. **`src/traditional.ts`**: `createStore(createState)` is called at line 70.

Two more files are affected only in some cases:

- **`src/index.ts`** does `export * from './vanilla.ts'`. It re-exports the new signature without any edit. You'd only touch it if you rename or remove the export.
- **`src/react.ts` and `src/traditional.ts` overloads**: both declare their own `create` overloads that use `StateCreator<T, [], Mos>`. These mirror the `createStore` overloads. If your change alters `StateCreator`, or the overload shape that `create` is meant to match, update these too.

The middleware files (`combine`, `devtools`, `immer`, `persist`, `redux`, `ssrSafe`, `subscribeWithSelector`) never call `createStore`. They only import the `StateCreator` and `StoreMutatorIdentifier` types, and several use `declare module '../vanilla'` for type augmentation. A change to `createStore` alone doesn't affect them. A change to `StateCreator` or to the `StoreMutators` interface would.

I searched only `src/`. Tests, docs and exa
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
`useSWR` avoids duplicate requests with the **`dedupingInterval`** option.

- **Default:** 2000 ms (`2 * 1000`), set in `src/_internal/utils/config.ts:76`.
- **Type:** declared in `src/_internal/types.ts:224`.

When a request starts for a key, SWR stores it in a shared in-flight map for that key. It removes the entry with `setTimeout(cleanupState, config.dedupingInterval)` (`src/index/use-swr.ts:606`). Any other `useSWR` call with the same key inside that window reuses the in-flight request instead of starting a new one.

I only searched for `dedupingInterval` and read the grep matches. I didn't open `use-swr.ts` to trace the in-flight map itself, so that part comes from how the option is used at line 606.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Files under `src/` that call `createStore` directly, and so would need to change if the call signature changes:

- **`src/react.ts`**: line 54, `createStore(createState)` inside `create`.
- **`src/traditional.ts`**: line 70, `createStore(createState)` inside `createWithEqualityFn`.

`src/index.ts` only has `export * from './vanilla.ts'`, so it re-exports the new signature without edits.

The middleware files (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) don't call `createStore`. They import types such as `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts` and augment its module with `declare module '../vanilla'`. They would only need changes if you also change those types, for example the `CreateStore` or `StateCreator` generics.

`createStore` itself is a curried overload: with an argument it creates the store, and with none it returns `createStoreImpl`. Changing the signature may mean changing the `CreateStore` type and the cast at `src/vanilla.ts:99-100`. That is inside `vanilla.ts`, not another file.

This is based on a text search for `createStore` and `vanilla`, not a type-check. Run `tsc` after the change to catch anything
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two other files under `src/` call `createStore` directly, so only those two would need changes:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside `create`.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`.

`src/index.ts` only does `export * from './vanilla.ts'`, so it re-exports whatever you change and needs no edit.

The middleware files (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) import types from `vanilla.ts`, such as `StateCreator` and `StoreMutatorIdentifier`. Some also use `declare module '../vanilla'` to augment it. None of them call `createStore`.

They would only be affected if your change touches those shared types, for example `StateCreator`, `StoreApi` or the mutator-identifier map. If you only change the `createStore` function or the `CreateStore` type, they are fine.

This search covered `src/` only. Tests and docs that call `createStore` would also need checking.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Files under `src/` that call or depend on `createStore` directly:

- **`src/react.ts`** calls `createStore(createState)` at line 54, inside `create`. It would break if the arguments or return type change.
- **`src/traditional.ts`** calls `createStore(createState)` at line 70, inside `createWithEqualityFn`. It has the same exposure.
- **`src/index.ts`** only does `export * from './vanilla.ts'`. It needs no edit, but the public API changes with the signature.

I only searched for the names and imports, so I didn't check how far a new return type would carry into each file. Whether `react.ts` and `traditional.ts` need edits depends on what changes. A new required parameter or a different return type would break their calls. An added optional parameter would not.

The middleware files import only types from `vanilla.ts`: `StateCreator` and `StoreMutatorIdentifier`. They don't use `createStore`. They would need changes only if you also change those types or the `declare module '../vanilla'` augmentations.

- `combine.ts`
- `redux.ts`
- `persist.ts`
- `immer.ts`
- `devtools.ts`
- `ssrSafe.ts`
- `subscribeWithSelector.ts`

`src/react/shallow.ts`, `src/shallow.ts` and `src/vanilla/shallow.
```
</details>
