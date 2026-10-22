# Kompactor A/B evidence

Real headless Claude Code sessions (`claude -p`, Claude Code 2.1.302 (Claude Code), model claude-sonnet-5-5), Kompactor 0.8.6 at level 3 (Balanced). 3 run(s) per task and condition; same prompt, tools, turn limit and budget cap in both conditions. Generated 2026-10-22.

**Total across 6 tasks: 517,145 › 451,030 tokens (-13%), cost $0.22 › $0.20 (-9%), output tokens -25%. Correct answers: 18/18 without, 18/18 with Kompactor.**

| Task | Lang | Tokens without (min–max) | Tokens with (min–max) | Δ tokens | Cost without | Cost with | Δ cost | Tool output chars | Turns | Correct |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| py-failing-tests | python | 67,496 (67k–68k) | 67,734 (68k–68k) | +0% | $0.035 | $0.035 | -1% | 3.4k › 3.4k | 2.0 › 2.0 | 3/3 › 3/3 |
| py-git-history | python | 116,436 (95k–128k) | 105,795 (95k–127k) | -9% | $0.040 | $0.037 | -7% | 0.9k › 0.3k | 3.7 › 3.3 | 3/3 › 3/3 |
| py-locate-code | python | 100,764 (101k–101k) | 77,971 (66k–101k) | -23% | $0.042 | $0.034 | -18% | 3.6k › 1.4k | 3.0 › 2.3 | 3/3 › 3/3 |
| go-locate-code | go | 65,847 (66k–66k) | 66,222 (66k–66k) | +1% | $0.029 | $0.030 | +3% | 0.5k › 0.5k | 2.0 › 2.0 | 3/3 › 3/3 |
| ts-locate-code | typescript | 99,806 (100k–100k) | 66,294 (66k–66k) | -34% | $0.039 | $0.031 | -22% | 1.0k › 0.3k | 3.0 › 2.0 | 3/3 › 3/3 |
| react-impact | react | 66,796 (67k–67k) | 67,014 (67k–67k) | +0% | $0.035 | $0.034 | -1% | 1.7k › 1.6k | 2.0 › 2.0 | 3/3 › 3/3 |

Tokens = input + cache writes + cache reads + output, summed over every API call in the session (what Claude Code bills). Δ is relative to the run without Kompactor. Correct means the final answer contained every expected fact (see `bench/tasks.json`).

## What happened in each run

Tool calls Claude made (from the session transcript), result size, and what Kompactor changed.

- **go-locate-code · baseline** (65,889 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|Requ (563 chars)
- **go-locate-code · baseline** (65,952 tokens, 2 turns): Grep func validateRequiredFlagGroups|func.*RequiredTogether|requi (776 chars)
- **go-locate-code · baseline** (65,701 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|func (271 chars)
- **go-locate-code · kompactor** (66,274 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|requ (691 chars) · Kompactor: nothing to compact
- **go-locate-code · kompactor** (66,277 tokens, 2 turns): Grep func validateRequiredFlagGroups|func validateFlagGroups|requ (691 chars) · Kompactor: nothing to compact
- **go-locate-code · kompactor** (66,116 tokens, 2 turns): Grep func validateRequiredFlagGroups|func.*[Rr]equiredFlagGroups| (186 chars) · Kompactor: nothing to compact
- **py-failing-tests · baseline** (67,491 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | grep -v PASSED | tail -80 (3,445 chars)
- **py-failing-tests · baseline** (67,454 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars)
- **py-failing-tests · baseline** (67,542 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars)
- **py-failing-tests · kompactor** (67,740 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars) · Kompactor: nothing to compact
- **py-failing-tests · kompactor** (67,706 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars) · Kompactor: nothing to compact
- **py-failing-tests · kompactor** (67,756 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,445 chars) · Kompactor: nothing to compact
- **py-git-history · baseline** (94,632 tokens, 3 turns): Bash git log -n 40 --format='C %H' --stat=200 | awk '/^C /{delete (205 chars); Bash git log -n 40 --name-only --format='' | grep '^src/' | sort  (122 chars)
- **py-git-history · baseline** (126,914 tokens, 4 turns): Bash git log -n 40 --format='@@%h' --name-only | awk '/^@@/{delet (189 chars); Bash git log -n 40 --format= --name-only -- src | sort | uniq -c  (120 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars)
- **py-git-history · baseline** (127,762 tokens, 4 turns): Bash git log -n 40 --name-only --format='@@%h' -- | awk '/^@@/{ne (150 chars); Bash git log -n 40 --name-only --format='' -- src (1,270 chars); Bash git log -n 40 --name-only --format='' | grep '^src/' (387 chars)
- **py-git-history · kompactor** (94,858 tokens, 3 turns): Bash git log -n 40 --format='C %h' --stat=200 | awk '/^C /{next}  (119 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars) · Kompactor: nothing to compact
- **py-git-history · kompactor** (95,307 tokens, 3 turns): Bash git log -n 40 --format='C %H' --stat=200 | awk '/^C /{delete (203 chars); Bash git log -n 40 --format= --name-only | grep '^src/' | sort |  (122 chars) · Kompactor: nothing to compact
- **py-git-history · kompactor** (127,219 tokens, 4 turns): Bash git log -n 40 --name-only --format='@@%h' | awk '/^@@/{delet (183 chars); Bash git log -n 40 --name-only --format= -- src | sort | uniq -c  (120 chars); Bash git log -n 40 --name-only --format= | grep '^src/' | sort |  (122 chars) · Kompactor: nothing to compact
- **py-locate-code · baseline** (100,737 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars)
- **py-locate-code · baseline** (100,889 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (422 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,326 chars)
- **py-locate-code · baseline** (100,667 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,133 chars)
- **py-locate-code · kompactor** (66,300 tokens, 2 turns): Grep def save_session|get_signing_serializer (287 chars) · Kompactor: nothing to compact
- **py-locate-code · kompactor** (66,473 tokens, 2 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (439 chars) · Kompactor: nothing to compact
- **py-locate-code · kompactor** (101,139 tokens, 3 turns): Grep def save_session|class SecureCookieSessionInterface|URLSafeT (290 chars); Read /private/tmp/claude-503/-Users-Amar-kompactor/5ea57f05-0ec4- (3,133 chars) · Kompactor: nothing to compact
- **react-impact · baseline** (66,835 tokens, 2 turns): Grep createStore|vanilla (1,666 chars)
- **react-impact · baseline** (66,761 tokens, 2 turns): Grep createStore|vanilla (1,666 chars)
- **react-impact · baseline** (66,791 tokens, 2 turns): Grep createStore|vanilla (1,666 chars)
- **react-impact · kompactor** (67,228 tokens, 2 turns): Grep createStore|vanilla (1,666 chars) · Kompactor: nothing to compact
- **react-impact · kompactor** (66,980 tokens, 2 turns): Grep createStore|vanilla (1,666 chars) · Kompactor: nothing to compact
- **react-impact · kompactor** (66,835 tokens, 2 turns): Grep createStore|from ['"].*vanilla (1,359 chars) · Kompactor: nothing to compact
- **ts-locate-code · baseline** (99,874 tokens, 3 turns): Grep dedupingInterval (260 chars); Grep FETCH\[|shouldStartNewRequest|dedupe (799 chars)
- **ts-locate-code · baseline** (99,850 tokens, 3 turns): Grep dedupingInterval (260 chars); Grep FETCH\[|shouldStartNewRequest|dedupe (799 chars)
- **ts-locate-code · baseline** (99,694 tokens, 3 turns): Grep dedupingInterval (260 chars); Grep shouldStartNewRequest|FETCH\[ (580 chars)
- **ts-locate-code · kompactor** (66,254 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact
- **ts-locate-code · kompactor** (66,308 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact
- **ts-locate-code · kompactor** (66,321 tokens, 2 turns): Grep dedupingInterval (260 chars) · Kompactor: nothing to compact

## Answers

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails out of 487: 482 passed, 4 were skipped, and 1 failed.

**Failing test:** `tests/test_helpers.py::TestStreaming::test_async_view`

**Key error:**
```
RuntimeError: Install Flask with the 'async' extra in order to use async views.
```

**Why:** The test calls an `async def` view. Flask's `app.async_to_sync` (`src/flask/app.py:1096`) needs `asgiref` to run it, and `asgiref` isn't installed in `.venv`. That makes this an environment problem, not a code bug. Installing the `async` extra (`pip install -e '.[async]'` or `pip install asgiref`) should fix it. I didn't change anything.

I only looked at the end of the output, so I didn't check why the 4 tests were skipped.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often were:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They are tied. The next most-touched files were `src/flask/sansio/app.py` and `src/flask/helpers.py`, with 2 commits each.

I counted with `git log -n 40 --name-only`, filtered to paths starting with `src/`. `--name-only` lists each file once per commit, so the counts are numbers of commits, not lines changed. I used `--name-only` instead of `--stat` because it's easier to count, and it lists the same files.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`
- **Method that serializes the session into the cookie:** `save_session` (line 337)

`save_session` does the serializing and signing at line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
```

It then passes `val` to `response.set_cookie(...)` at line 374.

The signing is done by the serializer that `get_signing_serializer` (line 303) returns. That method builds an `itsdangerous.URLSafeTimedSerializer`. It uses `app.secret_key`, with any `SECRET_KEY_FALLBACKS` listed before it. It also uses the class's `salt`, `serializer` (Flask's tagged JSON serializer), `key_derivation` and `digest_method`. If no secret key is set, it returns `None`.

The reverse direction is `open_session` (line 323). It calls `s.loads(val, max_age=...)` and returns an empty session if the signature is bad.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: `tests/test_helpers.py::TestStreaming::test_async_view`.

The error is `RuntimeError: Install Flask with the 'async' extra in order to use async views.` It is raised at `src/flask/app.py:1096` in `async_to_sync`. The `asgiref` import fails, so the `.venv` environment is missing the optional `async` extra.

The result was 482 passed, 4 skipped and 1 failed. This is an environment problem, not a code bug. Installing the extra, for example with `pip install asgiref`, should fix it. I didn't change anything.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`
- **Method:** `save_session` (line 337). It serializes and signs the session at line 373 with `self.get_signing_serializer(app).dumps(dict(session))`.

`get_signing_serializer` (line 303) in the same class builds the `URLSafeTimedSerializer` that does the signing. It uses the app's `secret_key`. The session is then written to the response with `response.set_cookie(...)`.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
The two most-changed files under `src/` in the last 40 commits are tied:

- `src/flask/cli.py`: 4 commits
- `src/flask/app.py`: 4 commits

The next closest are `src/flask/sansio/app.py` and `src/flask/helpers.py`, with 2 commits each.

I used `git log -n 40 --name-only` instead of `--stat`. It lists the same changed files, and the `--stat` pipeline needed an `awk` step that was blocked.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails out of 487 (482 passed, 4 skipped).

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Why: the test calls an async view, and `Flask.async_to_sync` (`src/flask/app.py:1096`) needs `asgiref` to run it. The `asgiref` import fails, so the `.venv` doesn't have the `async` extra installed.
- This looks like an environment problem, not a code bug. Installing `asgiref`, for example with `.venv/bin/pip install asgiref` or by installing Flask with the `async` extra, should fix it. I haven't tried that, since you asked me not to change anything.

I didn't change any code.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
**File:** `src/flask/sessions.py`

**Class:** `SecureCookieSessionInterface`, which starts at line 284.

**Method:** `save_session(self, app, session, response)`, which starts at line 337. It serializes and signs the session on line 373:

```python
val = self.get_signing_serializer(app).dumps(dict(session))
```

It then writes the result to the response with `response.set_cookie(name, val, ...)` on line 374.

Signing is handled by two pieces:

- **`get_signing_serializer(app)`** (line 303) builds an `itsdangerous.URLSafeTimedSerializer`. It uses `app.secret_key`, with any `SECRET_KEY_FALLBACKS` listed first so the current key is last. It also sets the salt, the JSON session serializer, and the key-derivation and digest settings. If no secret key is set, it returns `None`.
- **`dumps(dict(session))`** is an `itsdangerous` method. It produces the signed, timestamped, URL-safe string that becomes the cookie value.

The reverse direction is `open_session` (line 323), which calls `s.loads(val, max_age=...)` and falls back to an empty session on `BadSignature`.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits (no path filter), the two `src/` files changed most often are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

The two are tied. The next most-changed files are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each.

I counted file names from `git log -n 40 --name-only`. `--name-only` lists each file once per commit, so the counts match the number of commits. I ran the count without a path filter. A `-- src` filter would have made git pick the 40 latest commits that touch `src/`, which is a different set.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: `tests/test_helpers.py::TestStreaming::test_async_view`.

The error is `RuntimeError: Install Flask with the 'async' extra in order to use async views.` It is raised from `Flask.async_to_sync` at `src/flask/app.py:1096`. The `from asgiref.sync import async_to_sync` import fails with an `ImportError`, so `asgiref` isn't installed in `.venv`. This is an environment problem, not a code bug.

The other results: 482 passed, 4 skipped.

I didn't change any code. Installing `asgiref` (or `flask[async]`) into the venv should fix it.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session`, at line 337. It serializes and signs the session at line 373:
  ```python
  val = self.get_signing_serializer(app).dumps(dict(session))
  ```
  It then sets the result as the cookie value with `response.set_cookie(...)`.

`get_signing_serializer` (line 303) builds the signer. It returns an `itsdangerous.URLSafeTimedSerializer` configured with the app's `secret_key`. On the read side, `open_session` (line 324) uses the same serializer to load the cookie.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
In the 40 most recent commits, the two `src/` files changed most often are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They tie at 4. The next most-changed files are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each.

I counted with `git log --name-only` filtered to `src/` paths, not `--stat`. Each file is counted once per commit it appears in, so the numbers are commits touched.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails: 482 passed, 4 were skipped, and I didn't change any code.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- **Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- **Why:** The error comes from `Flask.async_to_sync` at `src/flask/app.py:1096`. That method tries `from asgiref.sync import async_to_sync`, gets an `ImportError`, and raises this instead. So `asgiref` isn't installed in `.venv`. This is a missing optional dependency, not a bug in the code.
- **Fix:** Run `.venv/bin/pip install asgiref`, or install Flask with the async extra (`pip install -e ".[async]"`). I haven't run either.

I only looked at the tail of the output, so I didn't check why the 4 tests were skipped.
```
</details>

<details><summary>py-locate-code · baseline · correct</summary>

```
The session cookie is created and signed in `src/flask/sessions.py`, in the class `SecureCookieSessionInterface`.

- **Method that serializes the session into the cookie:** `SecureCookieSessionInterface.save_session()` (line 337). At line 373 it runs `val = self.get_signing_serializer(app).dumps(dict(session))`. At line 374 it passes that value to `response.set_cookie(...)`.
- **Where the signing happens:** `SecureCookieSessionInterface.get_signing_serializer()` (line 303) builds an `itsdangerous.URLSafeTimedSerializer`. It uses `app.secret_key`, plus any `SECRET_KEY_FALLBACKS` for key rotation. It also passes the interface's `salt`, the JSON session serializer, and the `key_derivation` and `digest_method` settings. The serializer's `dumps()` does the serialization and the signature.
- **Reading the cookie back:** `open_session()` (line 323) calls `loads()` on the cookie value, with `max_age` taken from `permanent_session_lifetime`.
```
</details>

<details><summary>py-failing-tests · kompactor · correct</summary>

```
One test fails: `tests/test_helpers.py::TestStreaming::test_async_view`.

- **Error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.` It is raised at `src/flask/app.py:1096` in `async_to_sync`.
- **Why:** `asgiref` isn't installed in `.venv`, so the `from asgiref.sync import async_to_sync` import fails. This is an environment problem, not a code bug. Installing the `async` extra, or `asgiref`, should fix it.

The other 482 tests passed and 4 were skipped. I didn't change any code.
```
</details>

<details><summary>py-git-history · baseline · correct</summary>

```
In the 40 most recent commits (no path filter), the two `src/` files changed most often are tied at 4 commits each:

- `src/flask/app.py`: 4 commits
- `src/flask/cli.py`: 4 commits

No other `src/` file was touched in more than 2 commits. `src/flask/helpers.py` and `src/flask/sansio/app.py` each appear in 2.

I counted each commit once per file. I tallied by hand from `git log -n 40 --name-only --format='' | grep '^src/'`, because a pipe into `awk` needed approval.
```
</details>

<details><summary>py-locate-code · kompactor · correct</summary>

```
- **File:** `src/flask/sessions.py`
- **Class:** `SecureCookieSessionInterface`, which starts at line 284.
- **Method:** `save_session()`, at line 337. Line 373 does the serializing and signing: `val = self.get_signing_serializer(app).dumps(dict(session))`. The next call, `response.set_cookie(name, val, ...)`, writes the cookie.

`get_signing_serializer()` (line 303) builds the signer. It returns an itsdangerous `URLSafeTimedSerializer` keyed with `app.secret_key`, plus any `SECRET_KEY_FALLBACKS`. It also uses the class's `salt`, `key_derivation` and `digest_method`. The JSON serializer is `session_json_serializer`.

`open_session()` (line 323) reads the cookie back. It calls `s.loads(val, max_age=...)` and returns an empty session if the signature is bad.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The check is done by `validateRequiredFlagGroups` in `flag_groups.go`, at line 144.

It takes a map of flag groups to flag-set status. It returns an error if a group has some of its flags set but not all of them.

`Command.MarkFlagsRequiredTogether` (`flag_groups.go:33`) is the public method that registers a group. The validation function above is what enforces it.
```
</details>

<details><summary>py-git-history · kompactor · correct</summary>

```
In the 40 most recent commits (no path filter), the two src/ files changed most often are:

1. `src/flask/cli.py`: 4 commits
2. `src/flask/app.py`: 4 commits

They are tied at 4. The next closest are `src/flask/sansio/app.py` and `src/flask/helpers.py`, at 2 commits each.

I counted file names from `git log --name-only`. A file appears at most once per commit, so each count is a commit count.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
`validateRequiredFlagGroups` in `flag_groups.go:144` does this check. `ValidateFlagGroups` (line 79) calls it, and `MarkFlagsRequiredTogether` registers the groups through the `requiredAsGroupAnnotation` annotation.
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
`useSWR` avoids duplicate requests with the **`dedupingInterval`** option.

**Default value:** it is set to `2 * 1000` (2 seconds) at `src/_internal/utils/config.ts:76`. The type is declared in `src/_internal/types.ts:224`.

**How it works** (in `src/index/use-swr.ts`):
- In-flight requests are stored in a shared `FETCH` map, keyed by the serialized SWR key.
- Automatic revalidations, such as mount, focus and reconnect, run with `dedupe: true` (`WITH_DEDUPE`, line 78).
- At line 515, `shouldStartNewRequest = !FETCH[key] || !opts.dedupe`. If a request for that key is already in `FETCH` and `dedupe` is set, no new fetch starts. The hook reuses the existing promise, read at line 599 as `[newData, startAt] = FETCH[key]`.
- When a new request does start, `FETCH[key]` is set at line 586. After the request finishes, the entry is cleared with `setTimeout(cleanupState, config.dedupingInterval)` (line 606). So duplicate calls are suppressed for `dedupingInterval` ms after the request completes, not only while it is pending.

Calling `mutate` or the bound `mutate` revalidation doesn't pass `dedupe`, so it bypasses this and always starts a fresh request.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The function is `validateRequiredFlagGroups` in `flag_groups.go:144`.

It takes the per-group map of flag name to "is set" and returns an error if a group has some flags set and others not. `ValidateFlagGroups` (`flag_groups.go:79`) calls it. Groups are registered through `MarkFlagsRequiredTogether` (`flag_groups.go:33`).
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore` directly, so only those two would need to change:

- **`src/react.ts`**: line 54 calls `createStore(createState)` inside the `create` implementation.
- **`src/traditional.ts`**: line 70 calls `createStore(createState)` inside `createWithEqualityFn`.

Other files might need changes depending on what you alter:

- **`src/index.ts`** re-exports everything with `export * from './vanilla.ts'`. It needs no edit, but the new signature becomes part of the public API.
- **The middleware files** don't call `createStore`. They import types such as `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts`, and several augment the `'../vanilla'` module. If you change those types along with `createStore`, these would be affected:
  - `combine.ts`
  - `redux.ts`
  - `persist.ts`
  - `immer.ts`
  - `devtools.ts`
  - `ssrSafe.ts`
  - `subscribeWithSelector.ts`
- **`src/vanilla.ts` itself:** `createStoreImpl` and the `CreateStore` type sit next to `createStore` and would also need to match. The `createStore` definition at line 99 has curried and non-curried forms.

I only searched non-test files. Tests under `tests/` or in `*.test.*` files that call
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
The config option is `dedupingInterval`. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`.

The mechanism is in `src/index/use-swr.ts`. When a request starts, SWR stores the in-flight promise in a shared `FETCH` cache entry, keyed by the SWR key. Any other `useSWR` call with the same key during the deduping window reuses that promise instead of calling the fetcher again. After the request finishes, the `setTimeout(cleanupState, config.dedupingInterval)` at line 606 delays clearing that entry. That keeps deduping active for `dedupingInterval` ms after the request starts.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
`validateRequiredFlagGroups` in `flag_groups.go:144` does this check. Flags get grouped through `MarkFlagsRequiredTogether`, which stores the group in the `cobra_annotation_required_if_others_set` annotation. The exported `ValidateFlagGroups` (`flag_groups.go:79`) calls it.

I didn't open the function body, so I haven't confirmed the all-or-none logic itself.
```
</details>

<details><summary>go-locate-code · baseline · correct</summary>

```
The function is `validateRequiredFlagGroups` in `flag_groups.go:144`. It takes the per-group map of flag names to whether each is set, and returns an error if a group is only partly set.

`MarkFlagsRequiredTogether` (`flag_groups.go:33`) is the public method that registers a group. I didn't open the file, so I haven't read the body of `validateRequiredFlagGroups` itself.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
**Files that call `createStore` (these would break on a signature change):**
- `src/react.ts:54`: `const api = createStore(createState)` inside `createImpl`.
- `src/traditional.ts:70`: `const api = createStore(createState)` inside `createWithEqualityFnImpl`.

**Files that re-export it (these break only if the export shape changes):**
- `src/index.ts:1`: `export * from './vanilla.ts'`. It needs no edit unless you rename or move the export.

**Files that import types from `vanilla.ts` (these break only if you change `StateCreator`, `StoreMutatorIdentifier` or the other types, not `createStore` itself):**
- `src/middleware/combine.ts`
- `src/middleware/redux.ts`
- `src/middleware/persist.ts`
- `src/middleware/immer.ts`
- `src/middleware/devtools.ts`
- `src/middleware/ssrSafe.ts`
- `src/middleware/subscribeWithSelector.ts`
- `src/react.ts` and `src/traditional.ts` also import types from it.

Five of these middleware files (`redux`, `persist`, `immer`, `devtools` and `subscribeWithSelector`) also have `declare module '../vanilla'` blocks. They augment `StoreMutators`, so they would need updating if the change touches that interface.

Only `react.ts` and `traditional.ts` need edits for a
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
`useSWR` dedupes through the **`dedupingInterval`** config option. Its default is **2000 ms** (`2 * 1000`), set in `src/_internal/utils/config.ts:76`. The type is declared in `src/_internal/types.ts:224`.

How it works in `src/index/use-swr.ts`:
- Ongoing requests are stored in a shared `FETCH` map, keyed by the SWR key.
- In `revalidate`, line 515 computes `shouldStartNewRequest = !FETCH[key] || !opts.dedupe`. If a request for that key is already in flight and the call was made with `dedupe: true`, no new request starts. The caller reuses the existing promise from `FETCH[key]` (line 599).
- When a new request does start, it's registered in `FETCH[key]` at line 586.
- After the request finishes, the `FETCH[key]` entry is cleared by a `setTimeout(cleanupState, config.dedupingInterval)` at line 606. Until that timer fires, any other hook using the same key within the window reuses the result instead of fetching again.
- Automatic triggers such as mount, focus, and reconnect revalidate with `dedupe: true` (`WITH_DEDUPE`, line 78). A manual `mutate` or an explicit revalidate skips deduping.
```
</details>

<details><summary>go-locate-code · kompactor · correct</summary>

```
`validateRequiredFlagGroups` in `flag_groups.go:144`. It enforces groups registered with `MarkFlagsRequiredTogether`. I located it by name and didn't read the function body.

The neighbouring `validateOneRequiredFlagGroups` at line 167 is a different check: it requires at least one flag in the group.
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
The config option is `dedupingInterval`. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`. The type is declared at `src/_internal/types.ts:224`.

In `src/index/use-swr.ts`, the in-flight request is stored in a shared map keyed by the SWR key. While that entry exists, other `useSWR` calls with the same key reuse the pending promise instead of fetching again. After the request finishes, `setTimeout(cleanupState, config.dedupingInterval)` (line 606) keeps the entry for that interval, so calls made within the window are also deduplicated.

I only grepped for `dedupingInterval` and did not read the surrounding code in `use-swr.ts`, so the description of the shared map is from memory of SWR's design, not from this checkout.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Files under `src/` that call `createStore` and would need to change if its signature changes:

- **`src/react.ts`**: line 54 has `createStore(createState)` inside `create`.
- **`src/traditional.ts`**: line 70 has `createStore(createState)` inside `createWithEqualityFn`.

Files that probably don't need changes:

- **`src/index.ts`** only has `export * from './vanilla.ts'`, so it re-exports the new signature as is.
- **The middleware files** (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) import only the types `StateCreator` and `StoreMutatorIdentifier`. They never call `createStore`.
- **`src/middleware/{redux,persist,immer,devtools,subscribeWithSelector}.ts`** each have a `declare module '../vanilla'` block that augments `StoreMutators`. Those blocks matter only if your change touches `StoreMutators`, `StateCreator`, or `StoreApi`, and not just the `createStore` call signature.

I only searched for text matches. If the change alters the return type (`StoreApi<T>`) or the `CreateStore` type, `react.ts` and `traditional.ts` are the files affected, because they build on the returned `api`.

Tests and docs are outside `src/`, so I didn't check t
```
</details>

<details><summary>ts-locate-code · baseline · correct</summary>

```
useSWR deduplicates through a shared in-flight request cache and a time window controlled by the `dedupingInterval` option.

**How it works** (`src/index/use-swr.ts`):
- A global `FETCH` map holds the in-flight request for each key, as `[promise, startAt]`.
- On a fetch (line 515), `const shouldStartNewRequest = !FETCH[key] || !opts.dedupe`. If a request for that key is already in `FETCH` and `dedupe` is on, the hook doesn't start a new one. It reuses the existing promise (line 599: `[newData, startAt] = FETCH[key]`).
- When a new request is started, it is stored in `FETCH[key]` (line 586). After it finishes, cleanup is delayed with `setTimeout(cleanupState, config.dedupingInterval)` (line 606). So calls for the same key keep being deduplicated for that window, even after the response has arrived.

**Default value:** `dedupingInterval: 2 * 1000`, which is 2 seconds. It is set at `src/_internal/utils/config.ts:76`. The type is declared in `src/_internal/types.ts:224`.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Only two files under `src/` call `createStore`, so those are the ones a signature change would break:

- **`src/react.ts`**: line 54 has `const api = createStore(createState)`.
- **`src/traditional.ts`**: line 70 has `const api = createStore(createState)`.

`src/index.ts` only does `export * from './vanilla.ts'`. It re-exports the new signature and needs no edit.

The middleware files don't call `createStore`. They import types like `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts`. Several also use `declare module '../vanilla'` to augment its types: `redux`, `persist`, `immer`, `devtools` and `subscribeWithSelector`. Those would only need changes if your edit alters those shared types, such as `StateCreator` or the `StoreMutators` interface, and not just the `createStore` function itself.

I only searched `src/`. Tests and docs that call `createStore` are outside it, and I didn't check them.
```
</details>

<details><summary>react-impact · baseline · correct</summary>

```
Only two files under `src/` call `createStore`, so those are the ones a signature change would break directly:

- **`src/react.ts`**: line 54, `const api = createStore(createState)` in `create`'s implementation.
- **`src/traditional.ts`**: line 70, `const api = createStore(createState)` in `createWithEqualityFn`'s implementation.

A third file only re-exports it, so it needs no edit:

- **`src/index.ts`**: line 1, `export * from './vanilla.ts'`.

The middleware files (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) import only types such as `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts`. Several also augment `declare module '../vanilla'`. They don't reference `createStore`, so they're unaffected unless your change also touches those shared types.

Inside `vanilla.ts`, `createStoreImpl` (line 60) and the `CreateStore` type would change with it. `createStore` is also a curried overload: `createStore()` with no argument returns `createStoreImpl`. The `react.ts` and `traditional.ts` types, `UseBoundStore` and the `create`/`createWithEqualityFn` signatures, may also need updating if the change affects the returned store type.

I onl
```
</details>

<details><summary>ts-locate-code · kompactor · correct</summary>

```
**Config option:** `dedupingInterval`. Its default is `2 * 1000` (2 seconds), set at `src/_internal/utils/config.ts:76`. The type is declared at `src/_internal/types.ts:224`.

**How it works:** In `src/index/use-swr.ts`, the first call for a key stores the in-flight promise and a timestamp in the shared `FETCH` map. The same function then schedules `setTimeout(cleanupState, config.dedupingInterval)` (line 606). Any other `useSWR` call for that key during the interval reuses the stored promise instead of starting a new fetch. When the timer fires, the entry is cleared and a later call can fetch again.

I read only the `dedupingInterval` grep hits. I did not open the code around line 606, so the `FETCH` map detail comes from my memory of SWR's internals, not from this checkout.
```
</details>

<details><summary>react-impact · kompactor · correct</summary>

```
Files under `src/` that call `createStore`:

- `src/react.ts:54`: `create` calls `createStore(createState)`.
- `src/traditional.ts:70`: `createWithEqualityFn` calls `createStore(createState)`.

`src/index.ts` only does `export * from './vanilla.ts'`. It re-exports the new signature, so it needs no edit.

The middleware files in `src/middleware/` (`combine`, `redux`, `persist`, `immer`, `devtools`, `ssrSafe`, `subscribeWithSelector`) only import types such as `StateCreator` and `StoreMutatorIdentifier` from `vanilla.ts`. They are affected only if you change those types, not `createStore` itself.

If the change touches the `CreateStore` type or the curried form (`createStore()(...)`), also check the return-type usage in `src/react.ts` and `src/traditional.ts`. Both import types from `./vanilla.ts`.
```
</details>
