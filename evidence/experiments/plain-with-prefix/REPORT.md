# Kompact A/B evidence

Real headless Claude Code sessions (`claude -p`, Claude Code 2.1.304 (Claude Code), model claude-haiku-5-5, claude-sonnet-5-5), Kompact 0.3.0 at level 3 (Balanced). 3 run(s) per task and condition; same prompt, tools, turn limit and budget cap in both conditions. Generated 2026-10-20.

**Total across 3 tasks: 261,688 › 238,494 tokens (-9%), cost $0.14 › $0.13 (-4%), output tokens -13%. Correct answers: 9/9 without, 9/9 with Kompact.**

| Task | Lang | Tokens without (min–max) | Tokens with (min–max) | Δ tokens | Cost without | Cost with | Δ cost | Tool output chars | Turns | Correct |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| py-failing-tests | python | 76,012 (76k–76k) | 76,946 (77k–77k) | +1% | $0.047 | $0.047 | +2% | 3.4k › 4.1k | 2.0 › 2.0 | 3/3 › 3/3 |
| go-failing-test | go | 113,703 (113k–114k) | 88,948 (76k–115k) | -22% | $0.054 | $0.048 | -10% | 2.5k › 1.7k | 3.3 › 2.3 | 3/3 › 3/3 |
| ts-typecheck | typescript | 71,974 (72k–72k) | 72,600 (73k–73k) | +1% | $0.039 | $0.039 | -1% | 0.2k › 0.2k | 2.0 › 2.0 | 3/3 › 3/3 |

Tokens = input + cache writes + cache reads + output, summed over every API call in the session (what Claude Code bills). Δ is relative to the run without Kompact. Correct means the final answer contained every expected fact (see `bench/tasks.json`).

## What happened in each run

Tool calls Claude made (from the session transcript), result size, and what Kompact changed.

- **go-failing-test · baseline** (112,859 tokens, 3 turns): Bash go test -v ./... 2>&1 | grep -E "^(--- FAIL|FAIL|panic|\s+.* (716 chars); Bash go test -v -run TestFailGenFishCompletionFile . 2>&1 | head  (1,532 chars)
- **go-failing-test · baseline** (113,941 tokens, 3 turns): Bash go test -v ./... 2>&1 | grep -E "^(--- FAIL|FAIL|panic|\s+.* (2,028 chars); Read /tmp/claude-0/-home-user-Kompact/ee47be7b-ad62-53d9-9071-995 (539 chars)
- **go-failing-test · baseline** (114,308 tokens, 4 turns): Bash go test -v ./... 2>&1 | grep -E "^(--- FAIL|FAIL|panic|\s+.* (2,164 chars); Read /tmp/claude-0/-home-user-Kompact/ee47be7b-ad62-53d9-9071-995 (539 chars); Bash id -u (1 chars)
- **go-failing-test · kompact** (75,827 tokens, 2 turns): Bash go test -v ./... 2>&1 (1,550 chars, compacted) · Kompact: bash ×1 (−1,729 tokens)
- **go-failing-test · kompact** (75,856 tokens, 2 turns): Bash go test -v ./... (1,550 chars, compacted) · Kompact: bash ×1 (−1,729 tokens)
- **go-failing-test · kompact** (115,160 tokens, 3 turns): Bash go test -v ./... 2>&1 (1,550 chars, compacted); Read /tmp/claude-0/-home-user-Kompact/ee47be7b-ad62-53d9-9071-995 (581 chars) · Kompact: bash ×1 (−1,729 tokens), code_map ×1 (−0 tokens)
- **py-failing-tests · baseline** (75,983 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,448 chars)
- **py-failing-tests · baseline** (75,989 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,448 chars)
- **py-failing-tests · baseline** (76,064 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,448 chars)
- **py-failing-tests · kompact** (76,959 tokens, 2 turns): Bash .venv/bin/pytest tests -v (4,097 chars, compacted) · Kompact: bash ×1 (−1,281 tokens)
- **py-failing-tests · kompact** (76,888 tokens, 2 turns): Bash .venv/bin/pytest tests -v (4,097 chars, compacted) · Kompact: bash ×1 (−1,281 tokens)
- **py-failing-tests · kompact** (76,992 tokens, 2 turns): Bash .venv/bin/pytest tests -v (4,097 chars, compacted) · Kompact: bash ×1 (−1,281 tokens)
- **ts-typecheck · baseline** (71,850 tokens, 2 turns): Bash npx tsc --noEmit -p . 2>&1 | head -200 (182 chars)
- **ts-typecheck · baseline** (72,033 tokens, 2 turns): Bash npx tsc --noEmit -p . 2>&1 | tail -100 (182 chars)
- **ts-typecheck · baseline** (72,038 tokens, 2 turns): Bash npx tsc --noEmit -p . 2>&1 | head -200 (182 chars)
- **ts-typecheck · kompact** (72,511 tokens, 2 turns): Bash npx tsc --noEmit -p . (194 chars) · Kompact: nothing to compact
- **ts-typecheck · kompact** (72,617 tokens, 2 turns): Bash npx tsc --noEmit -p . (194 chars) · Kompact: nothing to compact
- **ts-typecheck · kompact** (72,672 tokens, 2 turns): Bash npx tsc --noEmit -p . (194 chars) · Kompact: nothing to compact

## Answers

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test failed: 482 passed, 4 skipped, 1 failed.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- **Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- **Why:** The test uses an async view. `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref`, which isn't installed in `.venv`, so it raises. This is a missing optional dependency in the environment, not a code bug. Installing `asgiref` (the `flask[async]` extra) should fix it.

I didn't change any code or install anything.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test fails (1 failed, 482 passed, 4 skipped):

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Why: the test defines an async view. `Flask.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync.async_to_sync`, and `asgiref` isn't installed in `.venv`. This is an environment problem, not a code bug. Installing the `async` extra (`pip install asgiref`, or `pip install -e .[async]`) should fix it.

I didn't change any code.
```
</details>

<details><summary>py-failing-tests · baseline · correct</summary>

```
One test failed out of 487: 482 passed, 4 were skipped, and I changed no code.

**Failing test:** `tests/test_helpers.py::TestStreaming::test_async_view`

**Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`

**Why:** The test defines an `async def` view. Flask's `app.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync`, and the import fails. The `asgiref` package isn't installed in `.venv`, so the cause is the environment and not a bug in Flask. Installing `asgiref` (the `flask[async]` extra) should fix it. I haven't done that, since you asked me not to change anything.
```
</details>

<details><summary>go-failing-test · baseline · correct</summary>

```
**Failing test:** `TestFailGenFishCompletionFile` in `fish_completions_test.go`. It's in the root `github.com/spf13/cobra` package, and I ran it alone to confirm. The `doc` package passes.

**Error:** a nil pointer dereference panic at `fish_completions_test.go:141`.

```
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
```

**Cause:** the test expects `GenFishCompletionFile` to return `os.ErrPermission`. It creates a file with mode `0400` and passes that path in. Line 141 is `t.Errorf("got: %s, ...", got.Error(), ...)`. `got` is `nil`, so `got.Error()` panics.

`GenFishCompletionFile` returned no error, so the file was writable. The sandbox is running as root (`/tmp/claude-0/...`), and root ignores file permission bits. The test is environment-dependent rather than a bug in cobra. It should pass as a non-root user.

The panic aborts the whole test binary, so any tests that would have run after it in the package didn't run. I made no code changes.
```
</details>

<details><summary>go-failing-test · baseline · correct</summary>

```
**`TestFailGenFishCompletionFile`** in the root `cobra` package fails, and it panics.

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
github.com/spf13/cobra.TestFailGenFishCompletionFile
    fish_completions_test.go:141
FAIL	github.com/spf13/cobra	0.292s
```

**Cause:** the test expects `GenFishCompletionFile` to fail with `os.ErrPermission`. It creates the file with mode `0400` (read-only) and tries to write to it. This session appears to run as root (the paths are under `/root` and `/tmp/claude-0`), and root ignores file permissions. The write succeeds, so `got` is `nil`.

The `errors.Is(got, os.ErrPermission)` check then fails. Line 141 calls `got.Error()` on that nil error, which causes the panic.

It's an environment issue rather than a code bug. The test should pass as a non-root user.

The panic aborted the root package's test run. Cobra's other test output (`TestCalledAs` and the rest) showed only passes in what I saw. I filtered the output, so I haven't confirmed that no other test failed in that package. The sub-packages ran 
```
</details>

<details><summary>ts-typecheck · baseline · correct</summary>

```
`npx tsc --noEmit -p .` reports 2 errors, both in `source/zz-kompact.ts`. I haven't fixed anything.

1. `source/zz-kompact.ts:1:14` – TS2322: Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2` – TS2322: Type 'number' is not assignable to type 'string'.
```
</details>

<details><summary>go-failing-test · baseline · correct</summary>

```
`TestFailGenFishCompletionFile` fails. It's in `fish_completions_test.go:141`, in package `github.com/spf13/cobra`, and it panics instead of failing cleanly:

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
github.com/spf13/cobra.TestFailGenFishCompletionFile
    fish_completions_test.go:141 +0x25b
FAIL	github.com/spf13/cobra	0.635s
```

**Cause:** The test creates a file with mode `0400` (read-only) and expects `GenFishCompletionFile` to return `os.ErrPermission` when it tries to write to it. This session runs as root (uid 0), and root ignores file permission bits. The write succeeds and `GenFishCompletionFile` returns `nil`. The test's error branch then calls `got.Error()` on that nil error, which causes the panic. I didn't change any code.

The panic aborts the whole `cobra` package run, so tests that would have run after it in that package never ran. The `TestCalledAs` and `TestGenManDoc` output shown above passed. I didn't see a result for every test.

Running as a non-root user should let this test pass.
```
</details>

<details><summary>ts-typecheck · baseline · correct</summary>

```
`npx tsc --noEmit -p .` reported 2 errors, both in `source/zz-kompact.ts`:

1. `source/zz-kompact.ts:1:14`: TS2322, Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2`: TS2322, Type 'number' is not assignable to type 'string'.

I didn't fix anything, as you asked.
```
</details>

<details><summary>ts-typecheck · baseline · correct</summary>

```
`npx tsc --noEmit -p .` reported 2 errors, both in `source/zz-kompact.ts`:

1. `source/zz-kompact.ts:1:14`: TS2322, Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2`: TS2322, Type 'number' is not assignable to type 'string'.

I haven't fixed anything, as you asked.
```
</details>

<details><summary>ts-typecheck · kompact · correct</summary>

```
`npx tsc --noEmit -p .` reported 2 errors, both in `source/zz-kompact.ts`. I haven't fixed anything.

- `source/zz-kompact.ts:1:14` — TS2322: Type 'string' is not assignable to type 'number'.
- `source/zz-kompact.ts:3:2` — TS2322: Type 'number' is not assignable to type 'string'.
```
</details>

<details><summary>py-failing-tests · kompact · correct</summary>

```
1 test failed, 482 passed, 4 skipped. I changed no code.

**Failure:** `tests/test_helpers.py::TestStreaming::test_async_view`
- **Key error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- **Why:** The test registers an `async def` view. `app.async_to_sync` (`src/flask/app.py:1096`) tries `from asgiref.sync import async_to_sync`, and that import fails with `ImportError`. So `asgiref` isn't installed in `.venv`. This is a missing optional dependency, not a code bug.

**Skipped (4):** The three dotenv tests are `test_load_dotenv`, `test_dotenv_path` and `test_disable_dotenv_from_env`. They skip with "dotenv is not installed". The output only shows those three, and the fourth skip was among the lines Kompact hid.

Installing `asgiref` (the `async` extra) should fix the failure.
```
</details>

<details><summary>go-failing-test · kompact · correct</summary>

```
**`TestFailGenFishCompletionFile`** fails, in `fish_completions_test.go:141`, with a nil pointer dereference panic:

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference [recovered]
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
```

The panic aborts the whole `github.com/spf13/cobra` package run (`FAIL github.com/spf13/cobra 0.411s`), so any tests that would have run after it didn't.

I haven't looked at line 141 yet, so I can't say why the value is nil. A likely cause is that the test expects an error from writing to an unwritable path. That can happen when the tests run as root, since root ignores file permissions, but I haven't checked this. I didn't change any code.

The `[Debug] [Error] ... unknown flag: --localroot` line is log output from another test. It isn't tied to this failure.
```
</details>

<details><summary>py-failing-tests · kompact · correct</summary>

```
One test fails: `tests/test_helpers.py::TestStreaming::test_async_view`.

**Error:** `RuntimeError: Install Flask with the 'async' extra in order to use async views.` It is raised at `src/flask/app.py:1096` in `async_to_sync`. The `asgiref` import fails because `asgiref` isn't installed in `.venv`, and the test defines an `async def` view.

The rest of the run was 482 passed and 4 skipped. The 3 dotenv tests in `test_cli.py` were skipped because `dotenv` isn't installed. The reason for the fourth skip was in the hidden output, so I haven't seen it.

I didn't change any code. Installing `asgiref` (the `flask[async]` extra) should fix the failure.
```
</details>

<details><summary>ts-typecheck · kompact · correct</summary>

```
`tsc` reported 2 errors, both in `source/zz-kompact.ts`:

1. `source/zz-kompact.ts:1:14`: TS2322, Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2`: TS2322, Type 'number' is not assignable to type 'string'.

I haven't fixed anything.
```
</details>

<details><summary>go-failing-test · kompact · correct</summary>

```
**`TestFailGenFishCompletionFile`** fails, in `fish_completions_test.go:141`, with a nil pointer dereference panic:

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
	github.com/spf13/cobra.TestFailGenFishCompletionFile
	fish_completions_test.go:141 +0x25b
FAIL	github.com/spf13/cobra	0.403s
```

The panic stops the test binary, so any tests that hadn't run yet in the `github.com/spf13/cobra` package never executed. The `[Debug] [Error] ... unknown flag: --localroot` line just before it is log output, not the failure.

The test most likely expects an error from generating the fish completion file and gets `nil` instead. That is a guess, because I didn't open line 141. You may be running as root, which can write to paths the test expects to be unwritable. I haven't changed any code.
```
</details>

<details><summary>ts-typecheck · kompact · correct</summary>

```
`tsc` reported 2 errors, both in `source/zz-kompact.ts`. I haven't fixed either.

1. `source/zz-kompact.ts:1:14` – TS2322: Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2` – TS2322: Type 'number' is not assignable to type 'string'.
```
</details>

<details><summary>py-failing-tests · kompact · correct</summary>

```
One test failed: 1 failed, 482 passed, 4 skipped. I changed no code.

**Failed**
- `tests/test_helpers.py::TestStreaming::test_async_view`
  - Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
  - Why: the test defines an `async def` view, so `Flask.async_to_sync` (`src/flask/app.py:1096`) tries to import `asgiref.sync`. That import fails because `asgiref` isn't installed in `.venv`. This is a missing optional dependency, not a code bug.

**Skipped**
- Three skips are in `tests/test_cli.py`, all with the reason "dotenv is not installed": `test_load_dotenv`, `test_dotenv_path` and `test_disable_dotenv_from_env`.
- The output shows only those three skips. The fourth skip was in the hidden passing-test lines, so I don't know which test it was or why it skipped.

Installing the `async` extra (`asgiref`) should fix the failure. I can do that if you'd like.
```
</details>

<details><summary>go-failing-test · kompact · correct</summary>

```
**`TestFailGenFishCompletionFile` fails**, in `fish_completions_test.go:141`. It panics, and the panic aborts the whole `github.com/spf13/cobra` package run:

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
...
github.com/spf13/cobra.TestFailGenFishCompletionFile(...)
	fish_completions_test.go:141 +0x25b
FAIL	github.com/spf13/cobra	0.423s
```

**Cause:** the test opens a file with mode `0400` and expects `GenFishCompletionFile` to return `os.ErrPermission`. This session runs as root (`/root/.ccr/...`), and root ignores file permission bits. The call succeeds and returns `nil`. The test then calls `got.Error()` on that `nil` error at line 141, which causes the nil-pointer panic.

This looks like an environment problem, not a code bug. The test would likely pass as a non-root user. I didn't change any code.

The panic stopped the run, so any tests after it in that package didn't run. Other failures could be hidden behind it. Kompact hid 809 passing-test lines, and the full output is available with `kompact show 1`.
```
</details>
