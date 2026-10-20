"""Realistic sample outputs used by the dashboard's live preview, so users can
see what Claude would receive at each quality/savings setting."""


def _pytest():
    passed = "\n".join(f"tests/test_api.py::test_endpoint_{i} PASSED{' ' * 30}[{i:3d}%]" for i in range(1, 61))
    return f"""============================= test session starts ==============================
platform linux -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0
rootdir: /home/dev/shop-api
configfile: pyproject.toml
plugins: anyio-4.4.0, cov-5.0.0
collected 61 items

{passed}
tests/test_orders.py::test_create_order FAILED                           [100%]

=================================== FAILURES ===================================
______________________________ test_create_order _______________________________

client = <FlaskClient <Flask 'shop'>>

    def test_create_order(client):
>       resp = client.post("/orders", json={{"sku": "A-1", "qty": 2}})

tests/test_orders.py:14:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
.venv/lib/python3.12/site-packages/werkzeug/test.py:1167: in post
    return self.open(*args, method="POST", **kw)
.venv/lib/python3.12/site-packages/flask/testing.py:235: in open
    response = super().open(
.venv/lib/python3.12/site-packages/werkzeug/test.py:1116: in open
    response_parts = self.run_wsgi_app(request.environ, buffered=buffered)
.venv/lib/python3.12/site-packages/werkzeug/test.py:988: in run_wsgi_app
    rv = run_wsgi_app(self.application, environ, buffered=buffered)
.venv/lib/python3.12/site-packages/werkzeug/test.py:1264: in run_wsgi_app
    app_rv = app(environ, start_response)
.venv/lib/python3.12/site-packages/flask/app.py:1498: in __call__
    return self.wsgi_app(environ, start_response)
.venv/lib/python3.12/site-packages/flask/app.py:1476: in wsgi_app
    response = self.handle_exception(e)
.venv/lib/python3.12/site-packages/flask/app.py:1473: in wsgi_app
    response = self.full_dispatch_request()
.venv/lib/python3.12/site-packages/flask/app.py:882: in full_dispatch_request
    rv = self.handle_user_exception(e)
.venv/lib/python3.12/site-packages/flask/app.py:880: in full_dispatch_request
    rv = self.dispatch_request()
.venv/lib/python3.12/site-packages/flask/app.py:865: in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
shop/orders.py:41: in create_order
    total = price_for(sku) * payload["qty"]
shop/pricing.py:18: in price_for
    return CATALOG[sku].price
E   KeyError: 'A-1'

shop/pricing.py:18: KeyError
=========================== short test summary info ============================
FAILED tests/test_orders.py::test_create_order - KeyError: 'A-1'
========================= 1 failed, 60 passed in 2.31s ========================="""


def _gotest():
    runs = "\n".join(f"=== RUN   TestHandler/case_{i}\n--- PASS: TestHandler/case_{i} (0.00s)" for i in range(1, 41))
    return f"""go: downloading github.com/stretchr/testify v1.9.0
go: downloading github.com/davecgh/go-spew v1.1.1
go: downloading gopkg.in/yaml.v3 v3.0.1
?   	example.com/shop/cmd/server	[no test files]
?   	example.com/shop/internal/version	[no test files]
=== RUN   TestHandler
{runs}
--- PASS: TestHandler (0.02s)
=== RUN   TestCheckout
--- FAIL: TestCheckout (0.00s)
panic: runtime error: invalid memory address or nil pointer dereference [recovered]
	panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x6b2f1a]

goroutine 21 [running]:
testing.tRunner.func1.2({{0x6f1e40, 0x9a8b30}})
	/usr/local/go/src/testing/testing.go:1631 +0x24a
testing.tRunner.func1()
	/usr/local/go/src/testing/testing.go:1634 +0x377
panic({{0x6f1e40?, 0x9a8b30?}})
	/usr/local/go/src/runtime/panic.go:770 +0x132
example.com/shop/internal/cart.(*Cart).Total(0x0)
	/home/dev/shop/internal/cart/cart.go:58 +0x1a
example.com/shop/internal/checkout.Checkout(0xc0000a6000)
	/home/dev/shop/internal/checkout/checkout.go:33 +0x45
example.com/shop/internal/checkout.TestCheckout(0xc0001044e0)
	/home/dev/shop/internal/checkout/checkout_test.go:21 +0x5d
testing.tRunner(0xc0001044e0, 0x7486a8)
	/usr/local/go/src/testing/testing.go:1689 +0xfb
created by testing.(*T).Run in goroutine 1
	/usr/local/go/src/testing/testing.go:1742 +0x390
FAIL	example.com/shop/internal/checkout	0.014s
ok  	example.com/shop/internal/cart	0.009s
ok  	example.com/shop/internal/http	0.031s
FAIL"""


def _vitest():
    ok = "\n".join(f" ✓ src/components/ProductCard.test.tsx > ProductCard > renders variant {i} {3 + i % 7}ms"
                   for i in range(1, 46))
    return f"""
 RUN  v2.0.5 /home/dev/storefront

{ok}
 ❯ src/hooks/useCart.test.ts (3 tests | 1 failed) 18ms
   × useCart > adds item and updates total 9ms
     → expected 0 to be 2400 // Object.is equality

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/hooks/useCart.test.ts > useCart > adds item and updates total
AssertionError: expected 0 to be 2400 // Object.is equality

- Expected
+ Received

- 2400
+ 0

 ❯ src/hooks/useCart.test.ts:27:32
     25|     act(() => result.current.add({{ sku: 'A-1', price: 1200 }}, 2));
     26|
     27|     expect(result.current.total).toBe(2400);
       |                                ^
     28|   }});
    at Object.toBe (node_modules/@vitest/expect/dist/index.js:1235:20)
    at Proxy.<anonymous> (node_modules/chai/chai.js:1661:16)
    at Proxy.methodWrapper (node_modules/chai/chai.js:1584:25)
    at node_modules/@vitest/runner/dist/index.js:146:14
    at node_modules/@vitest/runner/dist/index.js:61:7
    at runTest (node_modules/@vitest/runner/dist/index.js:960:17)
    at processTicksAndRejections (node:internal/process/task_queues:95:5)

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

 Test Files  1 failed | 4 passed (5)
      Tests  1 failed | 47 passed (48)
   Start at  10:42:11
   Duration  1.94s"""


def _gitlog():
    authors = ["Priya Shah <priya@shop.dev>", "Marco Rossi <marco@shop.dev>", "Lee Kim <lee@shop.dev>"]
    msgs = ["fix cart total rounding", "add checkout retry", "bump vite to 5.4", "refactor pricing service",
            "handle empty SKU", "add order webhook", "tidy logging", "split ProductCard", "cache catalog lookups",
            "go: upgrade to 1.23"]
    out = []
    for i in range(24):
        out.append(f"commit {('%040x' % (0x9f3a1c * (i + 7)))[-40:]}\nAuthor: {authors[i % 3]}\n"
                   f"Date:   Tue Oct {20 - i % 19} 1{i % 10}:0{i % 6}:12 2026 +0000\n\n    {msgs[i % 10]}\n\n"
                   f"    {'Longer explanation of why this change was needed and how it was tested.' if i % 2 else ''}\n")
    return "\n".join(out)


def _npm_build():
    chunks = "\n".join(f"dist/assets/{n}-{abs(hash(n)) % 10**8:08x}.js   {12 + i * 3.7:6.2f} kB │ gzip: {4 + i:5.2f} kB"
                       for i, n in enumerate(["index", "vendor", "react-dom", "router", "cart", "checkout", "product",
                                              "account", "search", "icons", "charts", "i18n", "auth", "admin"]))
    deps = "\n".join(f"npm http fetch GET 200 https://registry.npmjs.org/{p} {20 + i}ms (cache revalidated)"
                     for i, p in enumerate(["react", "react-dom", "vite", "typescript", "zod", "@tanstack/react-query",
                                            "clsx", "date-fns", "eslint", "vitest", "msw", "postcss"] * 6))
    return f"""{deps}
npm WARN deprecated inflight@1.0.6: This module is not supported, and leaks memory.
npm WARN deprecated glob@7.2.3: Glob versions prior to v9 are no longer supported
npm WARN deprecated rimraf@3.0.2: Rimraf versions prior to v4 are no longer supported

added 412 packages, and audited 413 packages in 9s

> storefront@1.4.0 build
> tsc -b && vite build

vite v5.4.2 building for production...
transforming...
✓ 1324 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.62 kB │ gzip:  0.38 kB
dist/assets/index-4c1e2b9a.css     18.40 kB │ gzip:  4.12 kB
{chunks}
(!) Some chunks are larger than 500 kB after minification.
✓ built in 6.81s"""


def _gitdiff():
    body = "\n".join(f"     const line{i} = compute({i});" for i in range(1, 19))
    lock = "\n".join(f'+    "node_modules/pkg-{i}": {{ "version": "1.{i}.0", "resolved": "https://registry.npmjs.org/pkg-{i}/-/pkg-{i}-1.{i}.0.tgz" }},'
                     for i in range(60))
    return f"""diff --git a/src/hooks/useCart.ts b/src/hooks/useCart.ts
index 3f2a1c4..9b7e2d0 100644
--- a/src/hooks/useCart.ts
+++ b/src/hooks/useCart.ts
@@ -10,30 +10,31 @@ export function useCart() {{
{body}
-  const total = items.reduce((sum, i) => sum + i.price, 0);
+  const total = items.reduce((sum, i) => sum + i.price * i.qty, 0);
{body}
diff --git a/package-lock.json b/package-lock.json
index 11aa22b..33cc44d 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,6 +1,66 @@
{lock}"""


SAMPLES = [
    {"id": "pytest", "short": "pytest", "lang": "python", "label": "Python · pytest -v (1 failure)", "cmd": "pytest -v", "text": _pytest()},
    {"id": "gotest", "short": "go test", "lang": "go", "label": "Go · go test -v ./... (panic)", "cmd": "go test -v ./...", "text": _gotest()},
    {"id": "vitest", "short": "vitest", "lang": "react", "label": "React · vitest run (1 failure)", "cmd": "npx vitest run",
     "text": _vitest()},
    {"id": "build", "short": "npm build", "lang": "typescript", "label": "TypeScript · npm install && npm run build",
     "cmd": "npm install && npm run build", "text": _npm_build()},
    {"id": "gitdiff", "short": "git diff", "lang": "typescript", "label": "git diff (with lock file)", "cmd": "git diff",
     "text": _gitdiff()},
    {"id": "gitlog", "short": "git log", "lang": "any", "label": "git log -n 24", "cmd": "git log -n 24", "text": _gitlog()},
]
