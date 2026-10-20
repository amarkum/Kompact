import io
import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

os.environ.setdefault("KOMPACT_HOME", tempfile.mkdtemp())

from kompact import config, graph, hooks  # noqa: E402


def make_repo(files: dict) -> str:
    root = tempfile.mkdtemp(prefix="kg-")
    for rel, body in files.items():
        p = Path(root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body))
    return root


PY = {
    "pyproject.toml": "[project]\nname='shop'\n",
    "shop/__init__.py": "from .cart import Cart\n",
    "shop/pricing.py": '''
        TAX_RATE = 0.2


        def price_for(sku):
            """Look up the catalogue price for a SKU."""
            return CATALOG[sku]


        class Discount:
            def apply(self, total):
                return total * 0.9
        ''',
    "shop/cart.py": '''
        from shop.pricing import price_for, Discount
        from . import pricing


        class BaseCart:
            pass


        class Cart(BaseCart):
            """Shopping cart that totals line items."""

            def total(self):
                subtotal = sum(price_for(s) for s in self.items)
                return Discount().apply(subtotal) * (1 + pricing.TAX_RATE)
        ''',
    "shop/api.py": '''
        from shop.cart import Cart


        def checkout(items):
            return Cart().total()
        ''',
    "tests/test_cart.py": '''
        from shop.cart import Cart


        def test_total():
            assert Cart().total() >= 0
        ''',
    "examples/demo.py": "from shop.api import checkout\ncheckout([])\n",
}

GO = {
    "go.mod": "module example.com/shop\n\ngo 1.22\n",
    "cart/cart.go": '''
        package cart

        import "example.com/shop/pricing"

        // Cart holds line items.
        type Cart struct {
        	Items []string
        }

        // Total sums prices.
        func (c *Cart) Total() int {
        	t := 0
        	for _, s := range c.Items {
        		t += pricing.PriceFor(s)
        	}
        	return t
        }
        ''',
    "cart/cart_test.go": '''
        package cart

        import "testing"

        func TestTotal(t *testing.T) {
        	c := &Cart{}
        	if c.Total() != 0 {
        		t.Fatal("bad")
        	}
        }
        ''',
    "pricing/pricing.go": '''
        package pricing

        // PriceFor returns the price of a SKU.
        func PriceFor(sku string) int {
        	return len(sku)
        }
        ''',
    "main.go": '''
        package main

        import (
        	"fmt"
        	"example.com/shop/cart"
        )

        func main() {
        	c := &cart.Cart{}
        	fmt.Println(c.Total())
        }
        ''',
}

TS = {
    "package.json": json.dumps({"name": "storefront", "dependencies": {"react": "^18"}}),
    "tsconfig.json": '{ // comments are allowed\n "compilerOptions": { "baseUrl": ".", "paths": { "@/*": ["src/*"] }, }, }',
    "src/lib/format.ts": '''
        /** Format cents as a price string. */
        export function formatPrice(cents: number): string;
        export function formatPrice(cents: number, currency?: string): string {
          return `${currency ?? "$"}${(cents / 100).toFixed(2)}`;
        }
        const withLogging = (fn: any) => fn;
        export const usePrice = withLogging((cents: number) => formatPrice(cents));
        ''',
    "src/components/Price.tsx": '''
        import { formatPrice } from "@/lib/format";

        export function Price({ cents }: { cents: number }) {
          return <span>{formatPrice(cents)}</span>;
        }
        ''',
    "src/components/ProductCard.tsx": '''
        import { Price } from "./Price";
        import { useCart } from "../hooks/useCart";

        export const ProductCard = ({ cents }: { cents: number }) => {
          const add = useCart();
          return <div onClick={add}><Price cents={cents} /></div>;
        };
        ''',
    "src/hooks/useCart.ts": '''
        export function useCart() {
          return () => undefined;
        }
        ''',
    "src/index.ts": 'export { ProductCard } from "./components/ProductCard";\n',
    "tests/price.test.tsx": '''
        import { Price } from "storefront/components/Price";
        import { formatPrice } from "../src/lib/format";

        test("formats", () => { expect(formatPrice(100)).toBe("$1.00"); render(<Price cents={1} />); });
        ''',
}


class PythonGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(PY)
        cls.stats = graph.build(cls.root)
        cls.g = graph.Graph(cls.root)

    def test_imports_resolve(self):
        edges = {(f, r) for f, t, r, n, _ in self.g.imports if r}
        self.assertIn(("shop/cart.py", "shop/pricing.py"), edges)  # absolute
        self.assertIn(("shop/api.py", "shop/cart.py"), edges)
        self.assertIn(("shop/__init__.py", "shop/cart.py"), edges)  # relative
        self.assertIn(("examples/demo.py", "shop/api.py"), edges)

    def test_symbols_and_kinds(self):
        kinds = {(s["name"], s["kind"], s["parent"]) for s in self.g.symbols}
        self.assertIn(("Cart", "class", ""), kinds)
        self.assertIn(("total", "method", "Cart"), kinds)
        self.assertIn(("TAX_RATE", "constant", ""), kinds)

    def test_callers_and_inheritance(self):
        rows, total = self.g.callers("price_for")
        self.assertIn(("shop/cart.py", "Cart.total"), {(r[0], r[2]) for r in rows})
        inherit = [r for r in self.g.refs if r[3] == "inherit"]
        self.assertIn(("shop/cart.py", "Cart", "BaseCart", "inherit"), [r[:4] for r in inherit])

    def test_impact_lists_dependents_and_tests(self):
        res, _ = graph.impact(self.root, "shop/pricing.py")
        self.assertIn("shop/cart.py", res["affected"])
        self.assertIn("shop/api.py", res["affected"])
        self.assertEqual(res["tests"], ["tests/test_cart.py"])
        text = graph.impact_text(self.root, "shop/pricing.py")
        self.assertIn("tests to run: tests/test_cart.py", text)
        self.assertIn("in examples/tooling", text)  # examples are reported separately

    def test_query_uses_names_and_docstrings(self):
        out = graph.query(self.root, "shopping cart total")
        self.assertIn("shop/cart.py", out.splitlines()[1])
        self.assertIn("catalogue", graph.query(self.root, "catalogue price lookup"))

    def test_type_checking_imports_do_not_make_cycles(self):
        root = make_repo({"pkg/a.py": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from pkg.b import B\n"
                                       "class A: pass\n",
                          "pkg/b.py": "from pkg.a import A\nclass B(A): pass\n",
                          "pkg/c.py": "from pkg.d import D\nclass C: pass\n",
                          "pkg/d.py": "from pkg.c import C\nclass D: pass\n"})
        cycles = graph.import_cycles(graph.load(root))
        self.assertEqual(cycles, [["pkg/c.py", "pkg/d.py"]])

    def test_explain(self):
        out = graph.explain_text(self.root, "price_for")
        self.assertIn("function at shop/pricing.py", out)
        self.assertIn("used by", out)

    def test_path_and_deps(self):
        self.assertIn("shop/cart.py", graph.path_text(self.root, "shop/api.py", "shop/pricing.py"))
        self.assertIn("shop/pricing.py", graph.deps_text(self.root, "shop/cart.py"))
        self.assertIn("price_for", graph.deps_text(self.root, "Cart.total"))

    def test_report_and_map(self):
        rep = graph.report(self.root)
        self.assertIn("## Core modules", rep)
        self.assertIn("shop/pricing.py", rep)
        self.assertNotIn("examples/demo.py", rep.split("## Areas")[0])
        self.assertLess(len(graph.session_map(self.root, 60)) // 3, 120)

    def test_incremental_rebuild(self):
        root = make_repo(PY)
        first = graph.build(root)
        self.assertEqual(first["parsed"], first["files"])
        time.sleep(0.01)
        Path(root, "shop/api.py").write_text("from shop.cart import Cart\n\ndef checkout2():\n    return Cart()\n")
        second = graph.build(root)
        self.assertEqual(second["parsed"], 1)
        self.assertIn("checkout2", {s["name"] for s in graph.Graph(root).symbols})
        os.remove(Path(root, "examples/demo.py"))
        graph.build(root)
        self.assertNotIn("examples/demo.py", graph.Graph(root).files)


class GoGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(GO)
        graph.build(cls.root)
        cls.g = graph.Graph(cls.root)

    def test_packages_are_units(self):
        self.assertEqual(self.g.unit_of("cart/cart.go"), "cart/")
        self.assertIn("pricing/", self.g.out_units["cart/"])
        self.assertIn("cart/", self.g.out_units["./"])

    def test_methods_with_receivers(self):
        total = [s for s in self.g.symbols if s["name"] == "Total"][0]
        self.assertEqual((total["kind"], total["parent"]), ("method", "Cart"))
        self.assertEqual(total["doc"], "Total sums prices.")

    def test_impact_names_test_files(self):
        res, _ = graph.impact(self.root, "pricing/pricing.go")
        self.assertIn("cart/cart.go", res["affected"])
        self.assertIn("cart/cart_test.go", res["tests"])

    def test_callers_across_packages(self):
        rows, _ = self.g.callers("PriceFor")
        self.assertIn(("cart/cart.go", "Cart.Total"), {(r[0], r[2]) for r in rows})


class TsGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(TS)
        graph.build(cls.root)
        cls.g = graph.Graph(cls.root)

    def test_import_resolution(self):
        edges = {(f, r) for f, t, r, n, _ in self.g.imports if r}
        self.assertIn(("src/components/Price.tsx", "src/lib/format.ts"), edges)  # tsconfig "@/*" alias
        self.assertIn(("src/components/ProductCard.tsx", "src/components/Price.tsx"), edges)  # no extension
        self.assertIn(("src/index.ts", "src/components/ProductCard.tsx"), edges)  # export ... from
        self.assertIn(("tests/price.test.tsx", "src/components/Price.tsx"), edges)  # package-name import

    def test_react_kinds(self):
        kinds = {s["name"]: s["kind"] for s in self.g.symbols}
        self.assertEqual(kinds["Price"], "component")
        self.assertEqual(kinds["ProductCard"], "component")
        self.assertEqual(kinds["useCart"], "hook")
        self.assertEqual(kinds["usePrice"], "hook")  # factory-made const
        self.assertEqual(sum(1 for s in self.g.symbols if s["name"] == "formatPrice"), 1)  # overloads merged

    def test_jsx_renders_count_as_usage(self):
        rows, _ = self.g.callers("Price")
        self.assertIn(("src/components/ProductCard.tsx", "render"), {(r[0], r[3]) for r in rows})

    def test_impact_reaches_tests(self):
        res, _ = graph.impact(self.root, "src/lib/format.ts")
        self.assertIn("src/components/Price.tsx", res["affected"])
        self.assertIn("tests/price.test.tsx", res["tests"])


class HookIntegrationTests(unittest.TestCase):
    def test_outline_carries_graph_context_and_session_map(self):
        files = dict(PY)
        body = "".join(f"    x{i} = {i}\n" for i in range(12))
        files["shop/big.py"] = "from shop.pricing import price_for\n\n" + "".join(
            f"def helper_{i}():\n{body}    return price_for('x')\n\n" for i in range(40))
        files["shop/api.py"] = "from shop.big import helper_1\nfrom shop.cart import Cart\n"
        root = make_repo(files)
        Path(root, ".git").mkdir()  # marks the project root
        data = config.read_file()
        data["projects"][str(Path(root).resolve())] = {"preset": 3, "overrides": {"session_map_tokens": 300}}
        config.write_file(data)
        try:
            out = self._hook("session-start", {"session_id": "gs", "source": "startup", "cwd": root})
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Code map of", ctx)
            self.assertIn("shop/pricing.py", ctx)
            out = self._hook("pre-read", {"session_id": "gs", "cwd": root,
                                          "tool_input": {"file_path": str(Path(root, "shop/big.py"))}})
            reason = out["hookSpecificOutput"]["permissionDecisionReason"]
            self.assertIn("Not an error", reason)
            self.assertIn("Graph: imported by shop/api.py", reason)
        finally:
            data = config.read_file()
            data["projects"].pop(str(Path(root).resolve()), None)
            config.write_file(data)

    def _hook(self, name, event):
        sys.stdin = io.StringIO(json.dumps(event))
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.run(name)
        sys.stdin = sys.__stdin__
        return json.loads(buf.getvalue())


if __name__ == "__main__":
    unittest.main()
