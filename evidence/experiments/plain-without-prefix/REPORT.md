# Kompact A/B evidence

Real headless Claude Code sessions (`claude -p`, Claude Code 2.1.304 (Claude Code), model claude-haiku-5-5, claude-sonnet-5-5), Kompact 0.3.0 at level 3 (Balanced). 3 run(s) per task and condition; same prompt, tools, turn limit and budget cap in both conditions. Generated 2026-10-20.

**Total across 3 tasks: 261,688 › 348,856 tokens (+33%), cost $0.14 › $0.19 (+36%), output tokens +30%. Correct answers: 9/9 without, 9/9 with Kompact.**

| Task | Lang | Tokens without (min–max) | Tokens with (min–max) | Δ tokens | Cost without | Cost with | Δ cost | Tool output chars | Turns | Correct |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| py-failing-tests | python | 76,012 (76k–76k) | 121,204 (121k–121k) | +59% | $0.047 | $0.065 | +40% | 3.4k › 10.9k | 2.0 › 3.0 | 3/3 › 3/3 |
| go-failing-test | go | 113,703 (113k–114k) | 155,146 (125k–215k) | +36% | $0.054 | $0.085 | +60% | 2.5k › 12.1k | 3.3 › 4.0 | 3/3 › 3/3 |
| ts-typecheck | typescript | 71,974 (72k–72k) | 72,506 (73k–73k) | +1% | $0.039 | $0.038 | -2% | 0.2k › 0.2k | 2.0 › 2.0 | 3/3 › 3/3 |

Tokens = input + cache writes + cache reads + output, summed over every API call in the session (what Claude Code bills). Δ is relative to the run without Kompact. Correct means the final answer contained every expected fact (see `bench/tasks.json`).

## What happened in each run

Tool calls Claude made (from the session transcript), result size, and what Kompact changed.

- **go-failing-test · baseline** (112,859 tokens, 3 turns): Bash go test -v ./... 2>&1 | grep -E "^(--- FAIL|FAIL|panic|\s+.* (716 chars); Bash go test -v -run TestFailGenFishCompletionFile . 2>&1 | head  (1,532 chars)
- **go-failing-test · baseline** (113,941 tokens, 3 turns): Bash go test -v ./... 2>&1 | grep -E "^(--- FAIL|FAIL|panic|\s+.* (2,028 chars); Read /tmp/claude-0/-home-user-Kompact/ee47be7b-ad62-53d9-9071-995 (539 chars)
- **go-failing-test · baseline** (114,308 tokens, 4 turns): Bash go test -v ./... 2>&1 | grep -E "^(--- FAIL|FAIL|panic|\s+.* (2,164 chars); Read /tmp/claude-0/-home-user-Kompact/ee47be7b-ad62-53d9-9071-995 (539 chars); Bash id -u (1 chars)
- **go-failing-test · kompact** (124,761 tokens, 3 turns): Bash go test -v ./... 2>&1 (10,040 chars); Bash go test -v ./... 2>&1 | grep -E -B2 -A15 -- '^(--- FAIL|FAIL (1,656 chars) · Kompact: nothing to compact
- **go-failing-test · kompact** (214,855 tokens, 6 turns): Bash go test -v ./... (10,040 chars); Bash go test -v ./... > /tmp/claude-0/-tmp-claude-0--home-user-Ko (58 chars); Grep ^\s*--- FAIL|^FAIL|^panic (318 chars); Bash go test -v ./... > /tmp/claude-0/-tmp-claude-0--home-user-Ko (11 chars); Grep ^\s*--- FAIL|^FAIL|^panic (1,800 chars) · Kompact: code_map ×1 (−0 tokens)
- **go-failing-test · kompact** (125,822 tokens, 3 turns): Bash go test -v ./... (10,040 chars); Bash go test -v ./... > /tmp/claude-0/-tmp-claude-0--home-user-Ko (2,458 chars) · Kompact: nothing to compact
- **py-failing-tests · baseline** (75,983 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,448 chars)
- **py-failing-tests · baseline** (75,989 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,448 chars)
- **py-failing-tests · baseline** (76,064 tokens, 2 turns): Bash .venv/bin/pytest tests -v 2>&1 | tail -80 (3,448 chars)
- **py-failing-tests · kompact** (121,040 tokens, 3 turns): Bash .venv/bin/pytest tests -v (10,040 chars); Bash .venv/bin/pytest tests -q --tb=line -rf (1,135 chars) · Kompact: nothing to compact
- **py-failing-tests · kompact** (121,444 tokens, 3 turns): Bash .venv/bin/pytest tests -v (10,040 chars); Bash .venv/bin/pytest tests -v --tb=short -p no:cacheprovider > / (341 chars) · Kompact: nothing to compact
- **py-failing-tests · kompact** (121,128 tokens, 3 turns): Bash .venv/bin/pytest tests -v (10,040 chars); Bash .venv/bin/pytest tests -q --tb=line -rf 2>&1 | grep -v PASSE (1,123 chars) · Kompact: nothing to compact
- **ts-typecheck · baseline** (71,850 tokens, 2 turns): Bash npx tsc --noEmit -p . 2>&1 | head -200 (182 chars)
- **ts-typecheck · baseline** (72,033 tokens, 2 turns): Bash npx tsc --noEmit -p . 2>&1 | tail -100 (182 chars)
- **ts-typecheck · baseline** (72,038 tokens, 2 turns): Bash npx tsc --noEmit -p . 2>&1 | head -200 (182 chars)
- **ts-typecheck · kompact** (72,507 tokens, 2 turns): Bash npx tsc --noEmit -p . (194 chars) · Kompact: nothing to compact
- **ts-typecheck · kompact** (72,509 tokens, 2 turns): Bash npx tsc --noEmit -p . (194 chars) · Kompact: nothing to compact
- **ts-typecheck · kompact** (72,502 tokens, 2 turns): Bash npx tsc --noEmit -p . (194 chars) · Kompact: nothing to compact

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

1. `source/zz-kompact.ts:1:14`: TS2322, Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2`: TS2322, Type 'number' is not assignable to type 'string'.
```
</details>

<details><summary>py-failing-tests · kompact · correct</summary>

```
One test fails: 1 failed, 482 passed, 4 skipped.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Key error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Raised at `src/flask/app.py:1096`.
- Why: the test serves an async view, and Flask needs the `asgiref` package for that. It comes with the `flask[async]` extra and isn't installed in `.venv`. This is an environment problem, not a code bug. Installing the extra (`pip install "flask[async]"`) should fix it. I haven't changed anything.
```
</details>

<details><summary>go-failing-test · kompact · correct</summary>

```
`TestFailGenFishCompletionFile` in the root `cobra` package is the failing test. It panics rather than failing an assertion, which aborts the package run.

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
github.com/spf13/cobra.TestFailGenFishCompletionFile(...)
    fish_completions_test.go:141
FAIL	github.com/spf13/cobra	0.324s
```

- **Cause:** The nil dereference is at `fish_completions_test.go:141`. I haven't opened the file, so I don't know which value is nil.
- **Other packages:** The `doc` package passes (`ok github.com/spf13/cobra/doc`).
- **Skipped tests:** The panic stopped the root package early, so any tests that would have run after it in that package didn't run.
- **Code changes:** I haven't changed any code.
```
</details>

<details><summary>ts-typecheck · kompact · correct</summary>

```
`npx tsc --noEmit -p .` reports 2 errors, both in `source/zz-kompact.ts`. I didn't fix them.

1. `source/zz-kompact.ts:1:14` – TS2322: Type 'string' is not assignable to type 'number'.
2. `source/zz-kompact.ts:3:2` – TS2322: Type 'number' is not assignable to type 'string'.
```
</details>

<details><summary>ts-typecheck · kompact · correct</summary>

```
`npx tsc --noEmit -p .` reports 2 errors, both in `source/zz-kompact.ts`. I haven't fixed either.

- `source/zz-kompact.ts:1:14`: TS2322, type `string` is not assignable to type `number`.
- `source/zz-kompact.ts:3:2`: TS2322, type `number` is not assignable to type `string`.
```
</details>

<details><summary>py-failing-tests · kompact · correct</summary>

```
One test fails: `tests/test_helpers.py::TestStreaming::test_async_view`. The run finished with 1 failed, 482 passed and 4 skipped.

The key error is `RuntimeError: Install Flask with the 'async' extra in order to use async views.`

The test uses an async view, which needs the optional async dependency (`asgiref`). That package isn't installed in `.venv`, so this looks like an environment problem and not a code bug. I didn't change any code.
```
</details>

<details><summary>go-failing-test · kompact · correct</summary>

```
**`TestFailGenFishCompletionFile`** in the root `github.com/spf13/cobra` package fails with a nil pointer dereference panic at `fish_completions_test.go:141`:

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference [recovered]
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
github.com/spf13/cobra.TestFailGenFishCompletionFile(...)
	fish_completions_test.go:141 +0x25b
FAIL	github.com/spf13/cobra	0.306s
```

The panic aborts the whole root package run, so the tests that come after it in that package never run. The `doc` subpackage passes (`ok github.com/spf13/cobra/doc`). I haven't changed any code.

I haven't opened the test to see why line 141 dereferences nil. This sandbox runs as root, though, and that test probably expects a file write to fail on a read-only path. Root can write there, so no error comes back. That is a guess, not something I checked.

The full output is saved at `/tmp/claude-0/-tmp-claude-0--home-user-Kompact-ee47be7b-ad62-53d9-9071-995e86384d2c-scratchpad-bench-cobra/2379dcc4-d1f7-45a8-8bc1-e77bad0afd5b/scratchpad/out.txt`.
```
</details>

<details><summary>py-failing-tests · kompact · correct</summary>

```
One test fails (1 failed, 482 passed, 4 skipped). I changed no code.

**`tests/test_helpers.py::TestStreaming::test_async_view`**
- Error: `RuntimeError: Install Flask with the 'async' extra in order to use async views.`
- Raised at `src/flask/app.py:1096`.
- Cause: the test uses an `async def` view, and Flask needs the `asgiref` package for that. The `.venv` apparently doesn't have it, since the `async` extra isn't installed.
- Fix: running `pip install "flask[async]"` (or `asgiref`) in the venv would probably make it pass. This is an environment gap, not a code bug.

The first run's output was truncated, so I re-ran with a quieter report. The same single failure showed up both times.
```
</details>

<details><summary>go-failing-test · kompact · correct</summary>

```
**`TestFailGenFishCompletionFile`** in the root `cobra` package fails with a nil pointer panic:

```
--- FAIL: TestFailGenFishCompletionFile (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference [recovered]
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x69629b]
github.com/spf13/cobra.TestFailGenFishCompletionFile(...)
	fish_completions_test.go:141
FAIL	github.com/spf13/cobra	0.307s
```

Because it panics, the run aborts there. Any `cobra` package tests that come after it in that run never execute. The `doc` package passes.

I haven't opened line 141 or run the test on its own. This run is a root user, so one possible cause is that the test expects a file-write error that root doesn't get (for example, writing to a read-only path). That's a guess.

I didn't change any code. The full output is in `/tmp/claude-0/-tmp-claude-0--home-user-Kompact-ee47be7b-ad62-53d9-9071-995e86384d2c-scratchpad-bench-cobra/0b9953c6-bc4e-4bd0-8a22-f14cddd24677/scratchpad/out.txt`.
```
</details>
