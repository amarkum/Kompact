# Contributing to Kompactor

Thanks for helping. Bug reports, ideas, new compaction rules and fixes are all welcome.

## Reporting a bug

[Open an issue](https://github.com/amarkum/kompactor/issues) with:

- what you ran and what you expected
- the output of `kompactor doctor`
- the Kompactor version (`kompactor --version`) and your OS
- for a compaction problem, the command and (if you can share it) the raw output from `kompactor show <id>`

Security problems go through private reporting instead; see [SECURITY.md](SECURITY.md).

## Setting up

Kompactor uses only the Python 3.9+ standard library, so there's nothing to install.

```bash
git clone https://github.com/amarkum/kompactor.git && cd kompactor
python -m unittest discover tests     # the full test suite
python -m kompactor --help            # run the CLI from the checkout
```

To try your changes in Claude Code, add your checkout as a marketplace and install from it:

```
/plugin marketplace add /path/to/kompactor
/plugin install amarkum@kompactor
```

For the dashboard with realistic data, fill a scratch home and open it:

```bash
KOMPACTOR_HOME=/tmp/kompactor-demo python scripts/demo.py
KOMPACTOR_HOME=/tmp/kompactor-demo python -m kompactor ui
```

## Making a change

- **Keep it dependency-free.** Kompactor runs inside every Claude Code tool call, on machines we don't control.
- **Never lose information.** A filter may drop noise, but it must keep errors, failures, the user's own stack frames and summary lines, and every shortened output must stay reachable with `kompactor show`.
- **Fail open.** If a hook can't do its job, the original output must pass through unchanged.
- **Add a test** in `tests/` for every filter or hook change. Filters are easiest to test with a real output sample.
- **Measure savings honestly.** If a change affects how much Claude reads, check it with `kompactor prove` on a real task, and don't count output Claude would never have read.
- Run `python -m unittest discover tests` and `claude plugin validate .` before opening a pull request.

## Adding a compaction rule

Most rules live in `kompactor/filters.py`, keyed by the command that produced the output. A good rule:

1. recognises the command (and leaves everything else alone),
2. keeps every failure, error and summary line,
3. comes with a test that feeds a real output sample through it and checks what's kept and what's dropped.

The dashboard's **Quality vs tokens** page previews filters on the samples in `kompactor/samples.py`, which is a quick way to see a rule's effect.

## Pull requests

- One focused change per pull request, with a short description of what changed and why.
- Update the README or `docs/` when behaviour users can see changes.
- Maintainers handle version bumps and releases (`scripts/bump_version.py`).

By contributing you agree that your work is released under the [MIT License](LICENSE).
