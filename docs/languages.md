# Languages

[← Back to the README](../README.md)

Kompactor detects each repo's languages (`pyproject.toml` › Python, `go.mod` › Go, `tsconfig.json`/`package.json` › TypeScript, a `react` or `next` dependency › React).

| | Python | Go | TypeScript / React |
|---|---|---|---|
| Library stack frames collapsed | `site-packages`, stdlib, `.venv` | `GOROOT`, `runtime/`, `pkg/mod` | `node_modules`, `node:internal`, `react-dom`, `next/dist` |
| Generated files (outline instead of a full read) | `*_pb2.py`, migrations | `*.pb.go`, `*_gen.go`, `zz_generated*`, mocks | `*.d.ts`, `*.min.js`, `dist/`, `.next/` |
| Lock files collapsed in diffs | `poetry.lock`, `uv.lock`, `Pipfile.lock` | `go.sum` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| Test runners | pytest, unittest, tox, nox | `go test`, gotestsum | jest, vitest, mocha, playwright |
| Code graph | `ast`: classes, functions, decorators, imports, calls | packages, structs, interfaces, methods | components, hooks, JSX renders, `tsconfig` paths, workspace packages |

More languages, detected per repo the same way:

| | Detected by | Library stack frames collapsed | Generated / lock files | Code graph |
|---|---|---|---|---|
| Rust | `Cargo.toml` | `/rustc/`, `.cargo/registry`, `std::` | `target/`; `Cargo.lock` | functions, structs, enums, traits, `impl` methods, `use crate::…`, `mod x;`, `impl Trait for Type` |
| Java / Kotlin / Scala | `pom.xml`, `build.gradle(.kts)`, `build.sbt` | `java.`, `kotlin.`, `scala.`, JUnit, Gradle | `build/generated/`, `target/`; `gradle.lockfile` | classes, interfaces, objects, methods, top-level functions, imports by package path, `extends` / `implements` / `:` |
| C# / .NET | `global.json`, `Directory.Build.props` | `System.`, `Microsoft.`, xUnit, NUnit | `bin/Debug`, `obj/`, `*.g.cs`, `*.Designer.cs`; `packages.lock.json` | classes, records, structs, methods, base types |
| Swift | `Package.swift` | `/usr/lib/swift`, XCTest | `.build/`, `DerivedData/`; `Package.resolved` | types, protocols, `func`s (in types and extensions), conformances |
| C / C++ | `CMakeLists.txt`, `meson.build` | `/usr/include`, libc, libstdc++ | `build/`, `*.pb.h`; `conan.lock` | classes, structs, namespaces, functions, `Class::method` definitions, `#include "…"`, base classes |
| Ruby | `Gemfile` | `/gems/`, the Ruby stdlib | `db/schema.rb`; `Gemfile.lock` | classes, modules, methods (`?`, `!`), `require` / `require_relative`, `<` superclasses |
| PHP | `composer.json` | `vendor/` | `vendor/`, `bootstrap/cache/`; `composer.lock` | classes, interfaces, traits, functions, `use` by namespace (PSR-4), `require`, `extends` / `implements` |

Test files are recognised for each (`*Test.java`, `*_spec.rb`, `tests/`, `CartTests.swift` and so on), so `impact` names the tests to run.

