# What Claude actually received

Task `react-failing-test` from [REPORT.md](REPORT.md): *"Run the tests with `npx vitest run --reporter=verbose` and tell me which test fails and why."* (zustand, 225 tests, one failing). Both results below are copied from the session transcripts of the A/B runs.

## Without Kompactor: 15,617 characters

Claude added its own `| tail -150` to keep the output manageable. The 150 lines it got back were mostly passing tests:

```
$ npx vitest run --reporter=verbose 2>&1 | tail -150
 ✓ |zustand| tests/devtools.test.tsx > when create devtools was called multiple times with `name` option undefined > when it receives a message of type... > JUMP_TO_ACTION... > updates state without recording with `message.state`, connections are isolated from each other 1ms
 ✓ |zustand| tests/devtools.test.tsx > when create devtools was called multiple times with `name` option undefined > when it receives a message of type... > JUMP_TO_ACTION... > does not throw for unparsable `message.state`, connections are isolated from each other 1ms
 … about 120 more lines of passing tests (14,117 characters) …
 ✓ |zustand| tests/vanilla/subscribe.test.tsx > subscribe() > should call listener immediately when fireImmediately is true 1ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  |zustand| tests/zz-kompact.test.ts > counter store > counts every increment
AssertionError: expected 2 to be 3 // Object.is equality
…
 Test Files  1 failed | 13 passed (14)
      Tests  1 failed | 224 passed (225)
```

Here the failure happened to land in the last 150 lines. A bigger suite, or a failure printed earlier, would have needed another run.

## With Kompactor: 1,039 characters

The plain-command rule had Claude run the command without a pipe. Kompactor's shell prefix ran it to completion, compacted it, and kept the exit code, so Claude Code still reported a failure. (The scratch path in vitest's `RUN` line is shortened here.)

```
$ npx vitest run --reporter=verbose
Exit code 1

 RUN  v4.1.10 …/bench/zustand

 × |zustand| tests/zz-kompact.test.ts > counter store > counts every increment 8ms
   → expected 2 to be 3 // Object.is equality

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  |zustand| tests/zz-kompact.test.ts > counter store > counts every increment
AssertionError: expected 2 to be 3 // Object.is equality

- Expected
+ Received

- 3
+ 2

 ❯ tests/zz-kompact.test.ts:12:36
     10|     store.getState().inc()
     11|     store.getState().inc()
     12|     expect(store.getState().count).toBe(3)
       |                                    ^
     13|   })
     14| })

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

 Test Files  1 failed | 13 passed (14)
      Tests  1 failed | 224 passed (225)
   Start at  06:20:37
   Duration  8.64s (transform 880ms, setup 3.35s, import 1.48s, tests 813ms, environment 15.29s)
[kompactor: 224 passing-test lines hidden]
[kompactor: 7398›251 tokens; full output: ~/.kompactor/bin/kompactor show 1]
```

At Balanced, vitest's own header and timing lines stay; Savings and Max savings drop them too.

Both arms answered correctly in all three runs. The Kompactor runs cost 37% less ($0.042 vs $0.066 median). Without Kompactor, a failing command is also a case Claude Code handles badly: it cuts the output to its first and last ~5,000 characters, and output hooks don't run. Kompactor's shell prefix is what gets this output compacted at all.
