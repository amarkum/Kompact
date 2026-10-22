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

os.environ.setdefault("KOMPACTOR_HOME", tempfile.mkdtemp())

from kompactor import config, graph, hooks, installer  # noqa: E402
installer.PATH_DIRS = ()  # never link `kompactor` into real PATH folders from tests
installer.EDITORS = ()  # never install or remove the real VS Code / Cursor extension from tests


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

    def test_symbol_impact_separates_users_from_importers(self):
        files = dict(TS)
        files["src/components/Badge.tsx"] = ('import { usePrice } from "@/lib/format";\n'
                                             'export const Badge = () => <b>{usePrice(1)}</b>;\n')
        root = make_repo(files)
        graph.build(root)
        res, _ = graph.impact(root, "formatPrice")
        self.assertEqual(res["affected"], ["src/components/Price.tsx"])  # callers of callers are not listed
        self.assertEqual(res["importers_only"], ["src/components/Badge.tsx"])
        self.assertIn("tests/price.test.tsx", res["tests"])
        text = graph.impact_text(root, "formatPrice")
        self.assertIn("uses it: src/components/Price.tsx", text)
        self.assertIn("import its module but not formatPrice: src/components/Badge.tsx", text)


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
            self.assertNotIn("Code map of", out["hookSpecificOutput"]["additionalContext"])  # not paid up front
            ev = {"session_id": "gs", "cwd": root, "tool_name": "Grep", "tool_input": {"pattern": "price"}}
            ctx = self._hook("post-explore", ev)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Code map of", ctx)  # first search of the session gets the map
            self.assertIn("shop/pricing.py", ctx)
            self.assertIsNone(self._hook("post-explore", ev))  # only once per session
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
        return json.loads(buf.getvalue()) if buf.getvalue() else None


if __name__ == "__main__":
    unittest.main()


MULTI = {
    "rust/Cargo.toml": "[package]\nname = 'ledger'\n",
    "rust/src/lib.rs": '''
        pub mod ledger;
        mod util;
        use crate::ledger::Ledger;

        /// Opens a ledger.
        pub fn open() -> Ledger { Ledger::new() }
        ''',
    "rust/src/ledger.rs": '''
        use crate::util::round_cents;

        pub struct Ledger { total: i64 }

        pub trait Balance { fn balance(&self) -> i64; }

        impl Ledger {
            /// Makes an empty ledger.
            pub fn new() -> Self { Ledger { total: 0 } }
            fn add<'a>(&mut self, s: &'a str) { self.total += round_cents(s.len() as i64); }
        }

        impl Balance for Ledger {
            fn balance(&self) -> i64 { self.total }
        }
        ''',
    "rust/src/util.rs": "pub fn round_cents(c: i64) -> i64 { c }\n",
    "java/src/main/java/com/shop/Cart.java": '''
        package com.shop;

        import com.shop.pricing.Pricing;

        /** A shopping cart. */
        public class Cart extends BaseCart implements Totals {
            private int items;

            public int total() {
                return Pricing.priceFor(items);
            }

            private void reset() { items = 0; }
        }
        ''',
    "java/src/main/java/com/shop/pricing/Pricing.java": '''
        package com.shop.pricing;

        public final class Pricing {
            public static int priceFor(int n) { return n * 100; }
        }
        ''',
    "java/src/test/java/com/shop/CartTest.java": '''
        package com.shop;
        import com.shop.Cart;
        class CartTest { void totals() { new Cart().total(); } }
        ''',
    "kotlin/app/src/main/kotlin/shop/Order.kt": '''
        package shop

        import shop.tax.applyTax

        data class Order(val cents: Int) : Priced {
            fun total(): Int = applyTax(cents)
            private fun hidden() = 1
        }
        ''',
    "kotlin/app/src/main/kotlin/shop/tax/Tax.kt": "package shop.tax\n\nfun applyTax(c: Int): Int = c * 2\n",
    "dotnet/Shop/Cart.cs": '''
        using Shop.Pricing;

        namespace Shop
        {
            /// <summary>A cart.</summary>
            public class Cart : BaseCart, ITotals
            {
                public int Total()
                {
                    return PriceList.PriceFor(3);
                }
            }
        }
        ''',
    "swift/Sources/Ledger/Ledger.swift": '''
        import Foundation

        public struct Ledger: Codable {
            public func balance() -> Int { return compute() }
            private func compute() -> Int { 0 }
        }
        ''',
    "cpp/src/cart.cpp": '''
        #include "cart.h"
        #include <vector>

        double Cart::total() const {
            return price_for(items_);
        }

        static int helper() { return 1; }
        ''',
    "cpp/src/cart.h": '''
        #pragma once
        #include "pricing.h"

        class Cart : public Base {
          public:
            double total() const;
        };
        ''',
    "cpp/src/pricing.h": "double price_for(int n);\n",
    "ruby/lib/shop/cart.rb": '''
        require_relative "pricing"

        module Shop
          # A cart full of items.
          class Cart < BaseCart
            def total
              Pricing.price_for(items)
            end

            def empty?
              items.zero?
            end
          end
        end
        ''',
    "ruby/lib/shop/pricing.rb": '''
        module Shop
          class Pricing
            def self.price_for(items)
              items.size * 100
            end
          end
        end
        ''',
    "php/src/Cart.php": '''
        <?php
        namespace App;

        use App\\Pricing\\PriceList;

        /** A cart. */
        class Cart extends BaseCart implements Totals
        {
            public function total(): int
            {
                return PriceList::priceFor(3);
            }

            private function reset(): void {}
        }
        ''',
    "php/src/Pricing/PriceList.php": "<?php\nnamespace App\\Pricing;\n\nclass PriceList { public static function priceFor(int $n): int { return $n; } }\n",
}


class MoreLanguagesGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(MULTI)
        graph.build(cls.root)
        cls.g = graph.Graph(cls.root)
        cls.syms = {(s["file"].split("/", 1)[0], s["name"]): s for s in cls.g.symbols}

    def sym(self, lang_dir, name):
        return self.syms[(lang_dir, name)]

    def test_languages_are_detected(self):
        langs = {info["lang"] for info in self.g.files.values()}
        self.assertEqual(langs, {"rust", "java", "kotlin", "csharp", "swift", "cpp", "ruby", "php"})

    def test_symbols_methods_and_visibility(self):
        cases = [("rust", "Ledger", "struct", "", 1), ("rust", "new", "method", "Ledger", 1),
                 ("rust", "add", "method", "Ledger", 0), ("rust", "Balance", "trait", "", 1),
                 ("java", "Cart", "class", "", 1), ("java", "reset", "method", "Cart", 0),
                 ("kotlin", "total", "method", "Order", 1), ("kotlin", "applyTax", "function", "", 1),
                 ("dotnet", "Total", "method", "Cart", 1), ("swift", "balance", "method", "Ledger", 1),
                 ("swift", "compute", "method", "Ledger", 0), ("cpp", "total", "method", "Cart", 1),
                 ("cpp", "helper", "function", "", 0), ("ruby", "empty?", "method", "Cart", 1),
                 ("php", "total", "method", "Cart", 1), ("php", "reset", "method", "Cart", 0)]
        for d, name, kind, parent, exported in cases:
            s = self.sym(d, name)
            self.assertEqual((s["kind"], s["parent"], s["exported"]), (kind, parent, exported), (d, name))
        self.assertEqual(self.sym("rust", "new")["doc"], "Makes an empty ledger.")
        self.assertEqual(self.sym("java", "Cart")["doc"], "A shopping cart.")
        self.assertEqual(self.sym("ruby", "Cart")["doc"], "A cart full of items.")

    def test_imports_resolve_to_files(self):
        edges = {(f, r) for f, t, r, n, _ in self.g.imports if r}
        for edge in [("rust/src/lib.rs", "rust/src/ledger.rs"), ("rust/src/lib.rs", "rust/src/util.rs"),
                     ("rust/src/ledger.rs", "rust/src/util.rs"),
                     ("java/src/main/java/com/shop/Cart.java", "java/src/main/java/com/shop/pricing/Pricing.java"),
                     ("kotlin/app/src/main/kotlin/shop/Order.kt", "kotlin/app/src/main/kotlin/shop/tax/Tax.kt"),
                     ("cpp/src/cart.cpp", "cpp/src/cart.h"), ("cpp/src/cart.h", "cpp/src/pricing.h"),
                     ("ruby/lib/shop/cart.rb", "ruby/lib/shop/pricing.rb"),
                     ("php/src/Cart.php", "php/src/Pricing/PriceList.php")]:
            self.assertIn(edge, edges)

    def test_callers_and_inheritance(self):
        for name, caller in [("priceFor", "java/src/main/java/com/shop/Cart.java"),
                             ("applyTax", "kotlin/app/src/main/kotlin/shop/Order.kt"),
                             ("round_cents", "rust/src/ledger.rs"), ("price_for", "ruby/lib/shop/cart.rb"),
                             ("price_for", "cpp/src/cart.cpp")]:
            rows, _ = self.g.callers(name)
            self.assertIn(caller, {r[0] for r in rows}, name)
        inherit = {(r[1], r[2]) for r in self.g.refs if r[3] == "inherit"}
        for pair in [("Cart", "BaseCart"), ("Cart", "Totals"), ("Ledger", "Balance"), ("Ledger", "Codable"),
                     ("Order", "Priced"), ("Cart", "ITotals"), ("Cart", "Base")]:
            self.assertIn(pair, inherit)

    def test_test_files_are_recognised(self):
        self.assertTrue(self.g.files["java/src/test/java/com/shop/CartTest.java"]["test"])
        res, _ = graph.impact(self.root, "java/src/main/java/com/shop/pricing/Pricing.java")
        self.assertIn("java/src/main/java/com/shop/Cart.java", res["affected"])


class McpServerTests(unittest.TestCase):
    """`kompactor mcp`: JSON-RPC over stdio, read-only graph tools."""

    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(PY)

    def run_server(self, *msgs):
        from kompactor import mcp
        out = io.StringIO()
        mcp.serve(self.root, io.StringIO("".join(json.dumps(m) + "\n" for m in msgs)), out)
        return {r["id"]: r for r in map(json.loads, out.getvalue().splitlines())}

    def call(self, i, tool, **args):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": tool, "arguments": args}}

    def test_handshake_and_tools(self):
        res = self.run_server({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                              {"jsonrpc": "2.0", "method": "notifications/initialized"},
                              {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                              {"jsonrpc": "2.0", "id": 3, "method": "nope"})
        self.assertEqual(res[1]["result"]["protocolVersion"], "2024-11-05")
        names = {t["name"] for t in res[2]["result"]["tools"]}
        self.assertTrue({"graph_query", "graph_callers", "graph_impact", "outline", "symbol"} <= names)
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in res[2]["result"]["tools"]))
        self.assertEqual(res[3]["error"]["code"], -32601)
        self.assertEqual(len(res), 3)  # the notification got no reply

    def test_tools_answer_from_the_graph(self):
        res = self.run_server(self.call(1, "graph_callers", name="price_for"),
                              self.call(2, "symbol", name="Cart.total"),
                              self.call(3, "outline", path="shop/cart.py"),
                              self.call(4, "outline", path="../../etc/passwd"),
                              self.call(5, "graph_callers"))
        self.assertIn("shop/cart.py", res[1]["result"]["content"][0]["text"])
        self.assertIn("def total", res[2]["result"]["content"][0]["text"])
        self.assertFalse(res[3]["result"]["isError"])
        self.assertTrue(res[4]["result"]["isError"])  # outside the project
        self.assertTrue(res[5]["result"]["isError"])  # missing argument


class CommunityTests(unittest.TestCase):
    def test_modules_that_import_each_other_form_areas(self):
        root = make_repo({
            "pyproject.toml": "[project]\nname='app'\n",
            "app/billing/invoice.py": "from app.billing.tax import rate\nfrom app.billing.money import cents\n",
            "app/billing/tax.py": "from app.billing.money import cents\ndef rate(): return cents(1)\n",
            "app/billing/money.py": "def cents(x): return x\n",
            "app/auth/login.py": "from app.auth.session import start\nfrom app.billing.invoice import *\n",
            "app/auth/session.py": "from app.auth.tokens import sign\ndef start(): return sign()\n",
            "app/auth/tokens.py": "def sign(): return 1\n",
        })
        graph.build(root)
        g = graph.Graph(root)
        areas = {c["name"]: set(c["units"]) for c in graph.communities(g)}
        self.assertEqual(areas["app/billing/"], {"app/billing/invoice.py", "app/billing/tax.py", "app/billing/money.py"})
        self.assertEqual(areas["app/auth/"], {"app/auth/login.py", "app/auth/session.py", "app/auth/tokens.py"})
        self.assertIn("## Communities", graph.report(root))
        v = graph.viz(root)
        self.assertEqual({a["name"] for a in v["areas"]}, {"app/billing/", "app/auth/"})
        self.assertTrue(all(n["area"] >= 0 for n in v["nodes"]))


class LinkConfidenceTests(unittest.TestCase):
    def test_callers_are_labelled_by_how_sure_the_link_is(self):
        root = make_repo({
            "pyproject.toml": "[project]\nname='app'\n",
            "app/jobs.py": "def run():\n    return 1\n",
            "app/tasks.py": "def run():\n    return 2\n\ndef only_here():\n    return 3\n",
            "app/cli.py": "from app.jobs import run\n\ndef main():\n    return run()\n",
            "app/loose.py": "def go():\n    return run() + only_here()\n",
        })
        graph.build(root)
        g = graph.Graph(root)
        jobs_run = [s for s in g.by_name["run"] if s["file"] == "app/jobs.py"]
        self.assertEqual(g.link("app/cli.py", jobs_run), "exact")
        self.assertEqual(g.link("app/loose.py", g.by_name["run"]), "ambiguous")
        self.assertEqual(g.link("app/loose.py", g.by_name["only_here"]), "likely")
        self.assertEqual(g.link("app/loose.py", []), "external")
        text = graph.callers_text(root, "run")
        self.assertIn("1 exact, 1 ambiguous", text)
        self.assertIn("app/loose.py:2  go  (ambiguous)", text)


class ExportAndHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(PY)
        graph.build(cls.root)

    def test_exports(self):
        d = json.loads(graph.export_text(self.root, "json"))
        self.assertIn({"source": "shop/cart.py", "target": "shop/pricing.py"}, d["imports"])
        self.assertIn("Cart.total", next(m for m in d["modules"] if m["id"] == "shop/cart.py")["symbols"])
        gml = graph.export_text(self.root, "graphml")
        self.assertIn('<edge source="shop/cart.py" target="shop/pricing.py"/>', gml)
        self.assertIn("-->", graph.export_text(self.root, "mermaid"))
        with self.assertRaises(ValueError):
            graph.export_text(self.root, "pdf")
        out = tempfile.mkdtemp()
        self.assertGreater(graph.export_obsidian(self.root, out), 0)
        self.assertIn("[[shop-pricing.py]]", Path(out, "shop-cart.py.md").read_text())

    def test_git_hook_installs_beside_existing_hooks_and_uninstalls(self):
        root = make_repo({"a.py": "x = 1\n"})
        Path(root, ".git", "hooks").mkdir(parents=True)
        mine = Path(root, ".git", "hooks", "post-commit")
        mine.write_text("#!/bin/sh\necho mine\n")
        self.assertEqual(len(graph.git_hook(root)), 3)
        self.assertEqual(graph.git_hook(root), [])  # already there
        self.assertIn("echo mine", mine.read_text())
        self.assertIn(graph.HOOK_MARK, mine.read_text())
        self.assertTrue(os.access(Path(root, ".git", "hooks", "post-merge"), os.X_OK))
        graph.git_hook(root, install=False)
        self.assertEqual(mine.read_text(), "#!/bin/sh\necho mine\n")
        self.assertFalse(Path(root, ".git", "hooks", "post-merge").exists())
        with self.assertRaises(FileNotFoundError):
            graph.git_hook(tempfile.mkdtemp())


class DocsInGraphTests(unittest.TestCase):
    def test_docs_sections_link_to_the_code_they_mention(self):
        root = make_repo({**PY, "docs/checkout.md": '''
            # Checkout

            How a cart is priced at checkout.

            ## Totals

            `Cart.total` adds tax after the discount; see [the cart](../shop/cart.py).

            ```python
            Cart().total()  # code blocks are not links
            ```
            ''', "notes.rst": "Pricing\n=======\n\nUses ``price_for``.\n"})
        graph.build(root)
        g = graph.Graph(root)
        sections = {(s["file"], s["name"]): s for s in g.symbols if s["kind"] == "section"}
        self.assertIn(("docs/checkout.md", "Totals"), sections)
        self.assertEqual(sections[("docs/checkout.md", "Checkout")]["doc"], "How a cart is priced at checkout.")
        self.assertIn(("notes.rst", "Pricing"), sections)
        self.assertIn(("docs/checkout.md", 8, "Totals"), g.docs_for(["total"]))
        self.assertIn(("docs/checkout.md", 8, "Totals"), g.docs_for(files=["shop/cart.py"]))
        self.assertNotIn(11, [ln for _, ln, _ in g.docs_for(["total"])])  # inside a fenced block
        self.assertIn("docs that mention it: docs/checkout.md:8 (Totals)", graph.impact_text(root, "shop/cart.py"))
        self.assertIn("documented in: docs/checkout.md:8 (Totals)", graph.explain_text(root, "Cart.total"))
        self.assertIn("docs/checkout.md", graph.query(root, "priced checkout"))
        self.assertTrue(g.is_aux_unit("docs/checkout.md"))  # docs never count as core modules
        self.assertNotIn("docs/checkout.md", {u for c in graph.communities(g) for u in c["units"]})
