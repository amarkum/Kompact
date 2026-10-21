# Security policy

## Reporting a problem

Please report security problems privately, not in a public issue: on GitHub, open the repository's **Security** tab and choose **Report a vulnerability**. Include what you found, how to reproduce it, and the Kompactor version (`kompactor --version`).

Fixes ship as a new release on GitHub, PyPI and the Claude Code plugin, and the report is credited unless you'd rather stay anonymous.

## Supported versions

Only the latest release gets security fixes. Update with `claude plugin update stackcone@kompactor`, `pipx upgrade kompactor`, or the newest `.vsix` from the Releases page.

## What Kompactor can access

Kompactor runs locally, through Claude Code's hooks. What it reads, stores and changes, and the fact that it sends nothing over the network, is described in the README's "What Kompactor runs and changes" section and in [PRIVACY.md](PRIVACY.md).
