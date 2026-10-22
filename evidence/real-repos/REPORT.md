# Compaction on real repositories

Real commands run in 6 real repositories (c, java, python, swift, typescript), 22 outputs in all, measured with `bench/real_repos.py` on 2026-10-22. No Claude session is involved: this measures what Kompactor's shell prefix and hooks would hand Claude for each output, against what Claude Code itself would show without Kompactor.

**Median change per output at level 3 (Balanced): -61%** (15 of 22 outputs smaller, 5 unchanged, 2 larger).

Totals are dominated by the largest output (631.1k tokens: `git diff HEAD~8 HEAD` in private-python-api); without it, 104.8k › 32.2k tokens, -69%.

**Across all 22 outputs, if Claude reads the 5 outputs Claude Code saves to a file: 735.9k › 34.5k tokens at level 3 (Balanced), -95%; level 1 -88%, level 5 -98%.**

Counting only Claude Code's 2 KB preview of those 5 saved outputs instead: 35.6k › 34.5k, -3%. The preview is cheaper but holds none of the results (no test summary, no diff body, no matches past the first lines), so an agent that needs them reads the file. Kompactor hands Claude the compacted whole output instead. Both figures are given because which one applies depends on the task.

**Failure lines that reached Claude, over 8 runs with a planted failure: 16/16 without Kompactor, 16/16 · 16/16 · 16/16 at levels 1 · 3 · 5.**

## Repositories

| Repository | Language | What it is |
|---|---|---|
| private-python-api (private, described only) | python | A private FastAPI service: about 100 source files, 327 pytest tests (some against the Firestore emulator). |
| kompactor (this repository) | python | Kompactor itself (public): 48 files, 107 unittest tests. |
| private-ts-server (private, described only) | typescript | A private TypeScript (Node) API server, tested with node --test. |
| cjson ([DaveGamble/cJSON](https://github.com/DaveGamble/cJSON) @ `6d9f2443ab`) | c | DaveGamble/cJSON (public C library). |
| swift-files ([JohnSundell/Files](https://github.com/JohnSundell/Files) @ `e85f2b4a8d`) | swift | JohnSundell/Files (public Swift package). |
| junit5-maven ([junit-team/junit5-samples](https://github.com/junit-team/junit5-samples) @ `53f60c4470`) | java | junit-team/junit5-samples, junit-jupiter-starter-maven (public Java, Maven + JUnit 5). |

## Every command

Tokens Claude would read. *Without* is Claude Code alone: the whole output up to 30,000 characters; past that, a 2 KB preview for a command that succeeded, or the first and last ~5,000 characters for one that failed. Levels 1, 3 and 5 are Kompactor's Max quality, Balanced and Max savings.

*Preview* marks an output Claude Code would save to a file; Δ is then against reading it in full.

| Repository | Command | Exit | Raw output | Without | Level 1 | Level 3 | Level 5 | Δ at level 3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| private-python-api | `pytest -v (all pass)` | 0 | 7.7k | 467 (preview) | 7.7k | 3.6k | 1.7k | -53% |
| private-python-api | `pytest -v (1 planted failure)` | 1 | 7.9k | 2.2k | 7.9k | 3.5k | 1.9k | +57% |
| private-python-api | `git log --stat -n 30` | 0 | 4.6k | 4.6k | 4.6k | 2.9k | 1.3k | -38% |
| private-python-api | `git diff HEAD~8 HEAD` | 0 | 631.1k | 515 (preview) | 6.6k | 2.2k | 1.2k | -100% |
| private-python-api | `grep -rn "def " app` | 0 | 14.6k | 581 (preview) | 12.3k | 3.6k | 1.3k | -75% |
| kompactor | `unittest -v (all pass)` | 0 | 2.2k | 2.2k | 2.2k | 125 | 119 | -94% |
| kompactor | `unittest -v (1 planted failure)` | 1 | 2.5k | 2.0k | 2.5k | 367 | 361 | -82% |
| kompactor | `git log --stat -n 30` | 0 | 4.8k | 4.8k | 4.8k | 2.5k | 1.2k | -48% |
| kompactor | `git diff HEAD~8 HEAD` | 0 | 27.4k | 503 (preview) | 9.5k | 4.5k | 2.3k | -84% |
| private-ts-server | `npm test (all pass)` | 0 | 5.6k | 5.6k | 5.6k | 2.6k | 1.6k | -54% |
| private-ts-server | `npm test (1 planted failure)` | 1 | 5.8k | 2.6k | 5.5k | 2.7k | 1.3k | +5% |
| private-ts-server | `tsc --noEmit (1 planted type error)` | 2 | 23 | 23 | 23 | 23 | 23 | +0% |
| private-ts-server | `git log --stat -n 30` | 0 | 22.0k | 505 (preview) | 7.7k | 3.8k | 1.8k | -83% |
| cjson | `make (clean build)` | 0 | 312 | 312 | 312 | 312 | 277 | +0% |
| cjson | `make test` | 0 | 272 | 272 | 272 | 272 | 133 | +0% |
| cjson | `make (1 planted compile error)` | 2 | 292 | 292 | 292 | 292 | 292 | +0% |
| swift-files | `swift build` | 0 | 47 | 47 | 47 | 47 | 47 | +0% |
| swift-files | `swift test (all pass)` | 0 | 2.7k | 2.7k | 2.7k | 132 | 134 | -95% |
| swift-files | `swift test (1 planted failure)` | 1 | 2.8k | 2.2k | 2.8k | 246 | 246 | -89% |
| junit5-maven | `mvn test (all pass)` | 0 | 866 | 866 | 866 | 112 | 112 | -87% |
| junit5-maven | `mvn test (1 planted failure)` | 1 | 1.2k | 1.2k | 1.2k | 413 | 413 | -67% |
| junit5-maven | `mvn test (1 planted compile error)` | 1 | 958 | 958 | 958 | 284 | 284 | -70% |

## Do failures survive?

Each planted failure has known lines (its message and file) that Claude needs to fix it. Counted: how many of them are in what Claude would read.

| Repository | Run | Raw output | Without Kompactor | Level 1 | Level 3 | Level 5 |
|---|---|---:|---|---|---|---|
| private-python-api | `pytest -v (1 planted failure)` | 7.9k | 2/2 | 2/2 | 2/2 | 2/2 |
| kompactor | `unittest -v (1 planted failure)` | 2.5k | 2/2 | 2/2 | 2/2 | 2/2 |
| private-ts-server | `npm test (1 planted failure)` | 5.8k | 2/2 | 2/2 | 2/2 | 2/2 |
| private-ts-server | `tsc --noEmit (1 planted type error)` | 23 | 2/2 | 2/2 | 2/2 | 2/2 |
| cjson | `make (1 planted compile error)` | 292 | 2/2 | 2/2 | 2/2 | 2/2 |
| swift-files | `swift test (1 planted failure)` | 2.8k | 2/2 | 2/2 | 2/2 | 2/2 |
| junit5-maven | `mvn test (1 planted failure)` | 1.2k | 2/2 | 2/2 | 2/2 | 2/2 |
| junit5-maven | `mvn test (1 planted compile error)` | 958 | 2/2 | 2/2 | 2/2 | 2/2 |

Where a failing run costs more with Kompactor: Claude Code keeps only the first and last ~5,000 characters of a failure, and in `pytest -v (1 planted failure)` (private-python-api, 2.2k › 3.5k), `npm test (1 planted failure)` (private-ts-server, 2.6k › 2.7k) that cut happened to keep the failure. Kompactor keeps every failure from the whole run plus the summary, which costs more here; the gain is that a failure in the middle of a long run can't be cut away.

## Examples (public repositories, level 3)

### kompactor: `unittest -v (1 planted failure)`

Without Kompactor Claude reads 2.0k tokens; with it, 367. What Kompactor hands Claude:

```
test_server_requires_token (test_kompactor.TurnAndSetupTests.test_server_requires_token) ... /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py:484: ResourceWarning: Implicitly cleaning up <HTTPError 403: 'Forbidden'>
  _warnings.warn(self.warn_message, ResourceWarning)
ok
test_planted (test_zz_planted.Planted.test_planted) ... FAIL

======================================================================
FAIL: test_planted (test_zz_planted.Planted.test_planted)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "<work>/kompactor/tests/test_zz_planted.py", line 6, in test_planted
    self.assertEqual(81, 90, "PLANTED-FAILURE: discount applied twice")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 81 != 90 : PLANTED-FAILURE: discount applied twice

----------------------------------------------------------------------
Ran 110 tests in 7.193s

FAILED (failures=1)
[kompactor: 108 passing-test lines hidden]
```

### cjson: `make (1 planted compile error)`

Without Kompactor Claude reads 292 tokens; with it, 292. What Kompactor hands Claude:

```
rm -f cJSON.o cJSON_Utils.o #delete object files
rm -f libcjson.dylib libcjson.dylib.1.7.19 libcjson.dylib.1 libcjson.a #delete cJSON
rm -f libcjson_utils.dylib libcjson_utils.dylib.1.7.19 libcjson_utils.dylib.1 libcjson_utils.a #delete cJSON_Utils
rm -f cJSON_test  #delete test
gcc -std=c89 -c -fPIC -pedantic -Wall -Werror -Wstrict-prototypes -Wwrite-strings -Wshadow -Winit-self -Wcast-align -Wformat=2 -Wmissing-prototypes -Wstrict-overflow=2 -Wcast-qual -Wc++-compat -Wundef -Wswitch-default -Wconversion -fstack-protector cJSON.c
gcc -std=c89 -shared -o libcjson.dylib.1.7.19 cJSON.o "" 
ln -s libcjson.dylib.1.7.19 libcjson.dylib.1
ln -s libcjson.dylib.1 libcjson.dylib
gcc -std=c89 -c -fPIC -pedantic -Wall -Werror -Wstrict-prototypes -Wwrite-strings -Wshadow -Winit-self -Wcast-align -Wformat=2 -Wmissing-prototypes -Wstrict-overflow=2 -Wcast-qual -Wc++-compat -Wundef -Wswitch-default -Wconversion -fstack-protector cJSON_Utils.c
cJSON_Utils.c:1487:21: error: use of undeclared identifier 'PLANTED_UNDECLARED_SYMBOL'
 1487 | int planted_value = PLANTED_UNDECLARED_SYMBOL;
      |                     ^
1 error generated.
make: *** [cJSON_Utils.o] Error 1
```

### swift-files: `swift test (1 planted failure)`

Without Kompactor Claude reads 2.2k tokens; with it, 246. What Kompactor hands Claude:

```
	 Executed 66 tests, with 0 failures (0 unexpected) in 0.056 (0.061) seconds
<work>/swift-files/Tests/FilesTests/PlantedTests.swift:5: error: -[FilesTests.PlantedTests testPlanted] : XCTAssertEqual failed: ("81") is not equal to ("90") - PLANTED-FAILURE: discount applied twice
Test Case '-[FilesTests.PlantedTests testPlanted]' failed (0.067 seconds).
Test Suite 'PlantedTests' failed at 2026-10-22 19:09:41.803.
	 Executed 1 test, with 1 failure (0 unexpected) in 0.067 (0.067) seconds
Test Suite 'FilesPackageTests.xctest' failed at 2026-10-22 19:09:41.803.
	 Executed 67 tests, with 1 failure (0 unexpected) in 0.123 (0.128) seconds
Test Suite 'All tests' failed at 2026-10-22 19:09:41.803.
	 Executed 67 tests, with 1 failure (0 unexpected) in 0.123 (0.128) seconds
Build complete! (0.78s)
[kompactor: 146 passing-test lines hidden]
```

### junit5-maven: `mvn test (1 planted failure)`

Without Kompactor Claude reads 1.2k tokens; with it, 413. What Kompactor hands Claude:

```
[INFO] Building junit-jupiter-starter-maven 1.0-SNAPSHOT
[INFO] Running com.example.project.CalculatorTests
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.061 s -- in com.example.project.CalculatorTests
[INFO] Running com.example.project.PlantedTests
[ERROR] Tests run: 1, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.008 s <<< FAILURE! -- in com.example.project.PlantedTests
[ERROR] com.example.project.PlantedTests.planted -- Time elapsed: 0.005 s <<< FAILURE!
org.opentest4j.AssertionFailedError: PLANTED-FAILURE: discount applied twice ==> expected: <90> but was: <81>
	at org.junit.jupiter.api.Assertions.assertEquals(Assertions.java:601)
	at com.example.project.PlantedTests.planted(PlantedTests.java:10)

[ERROR] Failures:
[ERROR]   PlantedTests.planted:10 PLANTED-FAILURE: discount applied twice ==> expected: <90> but was: <81>
[ERROR] Tests run: 6, Failures: 1, Errors: 0, Skipped: 0
[INFO] BUILD FAILURE
[INFO] Total time:  1.012 s
[INFO] Finished at: 2026-10-22T19:09:47+05:30
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:3.6.0:test (default-test) on project junit-jupiter-starter-maven: There are test failures.
[ERROR] See <work>/junit5-maven/junit-jupiter-starter-maven/target/surefire-reports for the individual test results.
[ERROR] See dump files (if any exist) [date].dump, [date]-jvmRun[N].dump and [date].dumpstream.
[ERROR] -> [Help 1]
[kompactor: 44 passing-test lines hidden]
```

## Reproduce

```bash
python bench/real_repos.py bench/real_repos.json /tmp/kompactor-real-repos --out evidence/real-repos
python bench/real_repos.py --report bench/real_repos.json evidence/real-repos
```

Cases marked private need their own repository; edit `bench/real_repos.json` to point at yours. Planted files are written to a copy (`git archive` of HEAD) or a fresh clone, never to the original.
