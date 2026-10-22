# Languages

[← Back to the README](../README.md)

Kompactor detects each repo's languages (`pyproject.toml` › Python, `go.mod` › Go, `tsconfig.json`/`package.json` › TypeScript, a `react` or `next` dependency › React). You can also pin them in the dashboard.

| | Python | Go | TypeScript / React |
|---|---|---|---|
| Library stack frames collapsed | `site-packages`, stdlib, `.venv` | `GOROOT`, `runtime/`, `pkg/mod` | `node_modules`, `node:internal`, `react-dom`, `next/dist` |
| Generated files (outline instead of a full read) | `*_pb2.py`, migrations | `*.pb.go`, `*_gen.go`, `zz_generated*`, mocks | `*.d.ts`, `*.min.js`, `dist/`, `.next/` |
| Lock files collapsed in diffs | `poetry.lock`, `uv.lock`, `Pipfile.lock` | `go.sum` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| Test runners | pytest, unittest, tox, nox | `go test`, gotestsum | jest, vitest, mocha, playwright |
| Code graph | `ast`: classes, functions, decorators, imports, calls | packages, structs, interfaces, methods | components, hooks, JSX renders, `tsconfig` paths, workspace packages |

