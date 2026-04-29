from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

TOTAL = 100
PASS_COUNT = 70
FAIL_COUNT = TOTAL - PASS_COUNT


@dataclass(frozen=True)
class Spec:
    language: str
    variant: str
    base_dir: Path
    test_path: str
    timeout: int


def python_simple_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            "def add_one(value: int) -> int:\n    return value + 1\n",
            "def add_one(value: int) -> int:\n    next_value = value\n    next_value += 1\n    return next_value\n",
            "def add_one(value: int) -> int:\n    return sum((value, 1))\n",
            "def add_one(value: int) -> int:\n    return (value).__add__(1)\n",
            "def add_one(value: int) -> int:\n    delta = 1\n    return value + delta\n",
        ]
        solution = impls[index % len(impls)]
    else:
        bugs = [
            "def add_one(value: int) -> int:\n    return value\n",
            "def add_one(value: int) -> int:\n    return value - 1\n",
            "def add_one(value: int) -> int:\n    return value + 2\n",
            "def add_one(value: int) -> int:\n    return abs(value) + 1\n",
            "def add_one(value: int) -> int:\n    return max(value, 0) + 1\n",
        ]
        solution = bugs[index % len(bugs)]

    test = (
        "import pytest\n"
        "from solution import add_one\n\n"
        "@pytest.mark.parametrize(\n"
        "    \"value, expected\",\n"
        "    [\n"
        "        (0, 1),\n"
        "        (1, 2),\n"
        "        (-1, 0),\n"
        "        (-50, -49),\n"
        "        (99, 100),\n"
        "    ],\n"
        ")\n"
        "def test_add_one_cases(value: int, expected: int) -> None:\n"
        "    assert add_one(value) == expected\n"
    )

    return {
        "solution.py": solution,
        "test_solution.py": test,
    }


def python_complex_files(index: int, passed: bool) -> dict[str, str]:
    init_py = 'from .math_ops import add, add_many\n\n__all__ = ["add", "add_many"]\n'

    if passed:
        impls = [
            (
                "def add(value: int, step: int = 1) -> int:\n"
                "    return value + step\n\n"
                "def add_many(start: int, deltas: list[int]) -> int:\n"
                "    total = start\n"
                "    for delta in deltas:\n"
                "        total = add(total, delta)\n"
                "    return total\n"
            ),
            (
                "def add(value: int, step: int = 1) -> int:\n"
                "    result = value\n"
                "    result += step\n"
                "    return result\n\n"
                "def add_many(start: int, deltas: list[int]) -> int:\n"
                "    return sum(deltas, start)\n"
            ),
            (
                "def add(value: int, step: int = 1) -> int:\n"
                "    return step + value\n\n"
                "def add_many(start: int, deltas: list[int]) -> int:\n"
                "    acc = start\n"
                "    for delta in deltas:\n"
                "        acc += delta\n"
                "    return acc\n"
            ),
        ]
        math_ops = impls[index % len(impls)]
    else:
        bugs = [
            (
                "def add(value: int, step: int = 1) -> int:\n"
                "    return value - step\n\n"
                "def add_many(start: int, deltas: list[int]) -> int:\n"
                "    total = start\n"
                "    for delta in deltas:\n"
                "        total = add(total, delta)\n"
                "    return total\n"
            ),
            (
                "def add(value: int, step: int = 1) -> int:\n"
                "    return value + step\n\n"
                "def add_many(start: int, deltas: list[int]) -> int:\n"
                "    return start\n"
            ),
            (
                "def add(value: int, step: int = 1) -> int:\n"
                "    return value + step + 1\n\n"
                "def add_many(start: int, deltas: list[int]) -> int:\n"
                "    return sum(deltas, start)\n"
            ),
        ]
        math_ops = bugs[index % len(bugs)]

    test = (
        "from app.math_ops import add, add_many\n\n"
        "def test_add_default_step() -> None:\n"
        "    assert add(5) == 6\n\n"
        "def test_add_custom_step() -> None:\n"
        "    assert add(3, 4) == 7\n\n"
        "def test_add_many_sequence() -> None:\n"
        "    assert add_many(1, [2, 3, 4]) == 10\n\n"
        "def test_add_many_with_negatives() -> None:\n"
        "    assert add_many(10, [5, -3, -2]) == 10\n"
    )

    return {
        "app/__init__.py": init_py,
        "app/math_ops.py": math_ops,
        "tests/test_math_ops.py": test,
    }


def python_nested_files(index: int, passed: bool) -> dict[str, str]:
    pkg_init = 'from .core.addition import add_many, add_one\n\n__all__ = ["add_one", "add_many"]\n'
    core_init = 'from .addition import add_many, add_one\n\n__all__ = ["add_one", "add_many"]\n'

    if passed:
        impls = [
            (
                "def add_one(value: int) -> int:\n"
                "    return value + 1\n\n"
                "def add_many(start: int, increments: list[int]) -> int:\n"
                "    total = start\n"
                "    for inc in increments:\n"
                "        total += inc\n"
                "    return total\n"
            ),
            (
                "def add_one(value: int) -> int:\n"
                "    next_value = value\n"
                "    next_value += 1\n"
                "    return next_value\n\n"
                "def add_many(start: int, increments: list[int]) -> int:\n"
                "    return sum(increments, start)\n"
            ),
        ]
        addition = impls[index % len(impls)]
    else:
        bugs = [
            (
                "def add_one(value: int) -> int:\n"
                "    return value\n\n"
                "def add_many(start: int, increments: list[int]) -> int:\n"
                "    total = start\n"
                "    for inc in increments:\n"
                "        total += inc\n"
                "    return total\n"
            ),
            (
                "def add_one(value: int) -> int:\n"
                "    return value + 1\n\n"
                "def add_many(start: int, increments: list[int]) -> int:\n"
                "    return start - sum(increments)\n"
            ),
            (
                "def add_one(value: int) -> int:\n"
                "    return value + 2\n\n"
                "def add_many(start: int, increments: list[int]) -> int:\n"
                "    return sum(increments, start)\n"
            ),
        ]
        addition = bugs[index % len(bugs)]

    test = (
        "from services.calculator.core.addition import add_many, add_one\n\n"
        "def test_add_one_values() -> None:\n"
        "    assert add_one(9) == 10\n"
        "    assert add_one(-3) == -2\n\n"
        "def test_add_many_values() -> None:\n"
        "    assert add_many(3, [1, 2, 3]) == 9\n"
        "    assert add_many(0, [5, -2, -1]) == 2\n"
    )

    return {
        "services/calculator/__init__.py": pkg_init,
        "services/calculator/core/__init__.py": core_init,
        "services/calculator/core/addition.py": addition,
        "tests/unit/test_addition.py": test,
    }


def js_simple_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            "function addOne(value) {\n  return value + 1;\n}\n\nmodule.exports = { addOne };\n",
            "const addOne = (value) => value + 1;\n\nmodule.exports = { addOne };\n",
            "function addOne(value) {\n  const nextValue = value + 1;\n  return nextValue;\n}\n\nmodule.exports = { addOne };\n",
        ]
        solution = impls[index % len(impls)]
    else:
        bugs = [
            "function addOne(value) {\n  return value;\n}\n\nmodule.exports = { addOne };\n",
            "function addOne(value) {\n  return value - 1;\n}\n\nmodule.exports = { addOne };\n",
            "function addOne(value) {\n  return Math.abs(value) + 1;\n}\n\nmodule.exports = { addOne };\n",
        ]
        solution = bugs[index % len(bugs)]

    test = (
        "const test = require(\"node:test\");\n"
        "const assert = require(\"node:assert/strict\");\n"
        "const { addOne } = require(\"./solution\");\n\n"
        "test(\"addOne handles integer inputs\", () => {\n"
        "  assert.equal(addOne(0), 1);\n"
        "  assert.equal(addOne(10), 11);\n"
        "  assert.equal(addOne(-1), 0);\n"
        "});\n"
    )

    return {
        "solution.js": solution,
        "test_solution.test.js": test,
    }


def js_complex_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            (
                "function add(value, step = 1) {\n"
                "  return value + step;\n"
                "}\n\n"
                "function addMany(start, deltas) {\n"
                "  return deltas.reduce((acc, item) => add(acc, item), start);\n"
                "}\n\n"
                "module.exports = { add, addMany };\n"
            ),
            (
                "function add(value, step = 1) {\n"
                "  const nextValue = value + step;\n"
                "  return nextValue;\n"
                "}\n\n"
                "function addMany(start, deltas) {\n"
                "  let total = start;\n"
                "  for (const delta of deltas) {\n"
                "    total = add(total, delta);\n"
                "  }\n"
                "  return total;\n"
                "}\n\n"
                "module.exports = { add, addMany };\n"
            ),
        ]
        math_add = impls[index % len(impls)]
    else:
        bugs = [
            (
                "function add(value, step = 1) {\n"
                "  return value - step;\n"
                "}\n\n"
                "function addMany(start, deltas) {\n"
                "  return deltas.reduce((acc, item) => add(acc, item), start);\n"
                "}\n\n"
                "module.exports = { add, addMany };\n"
            ),
            (
                "function add(value, step = 1) {\n"
                "  return value + step + 1;\n"
                "}\n\n"
                "function addMany(start, deltas) {\n"
                "  return deltas.reduce((acc, item) => acc + item, start);\n"
                "}\n\n"
                "module.exports = { add, addMany };\n"
            ),
            (
                "function add(value, step = 1) {\n"
                "  return value + step;\n"
                "}\n\n"
                "function addMany(start, deltas) {\n"
                "  return start;\n"
                "}\n\n"
                "module.exports = { add, addMany };\n"
            ),
        ]
        math_add = bugs[index % len(bugs)]

    test = (
        "const test = require(\"node:test\");\n"
        "const assert = require(\"node:assert/strict\");\n"
        "const { add, addMany } = require(\"../src/index\");\n\n"
        "test(\"add default and custom step\", () => {\n"
        "  assert.equal(add(7), 8);\n"
        "  assert.equal(add(3, 4), 7);\n"
        "});\n\n"
        "test(\"addMany handles sequences\", () => {\n"
        "  assert.equal(addMany(1, [2, 3, 4]), 10);\n"
        "  assert.equal(addMany(10, [5, -3, -2]), 10);\n"
        "});\n"
    )

    return {
        "src/math/add.js": math_add,
        "src/index.js": 'const { add, addMany } = require("./math/add");\n\nmodule.exports = { add, addMany };\n',
        "test/math_ops.test.js": test,
    }


def js_nested_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            (
                "function addOne(value) {\n"
                "  return value + 1;\n"
                "}\n\n"
                "function addMany(start, increments) {\n"
                "  return increments.reduce((acc, inc) => acc + inc, start);\n"
                "}\n\n"
                "module.exports = { addOne, addMany };\n"
            ),
            (
                "function addOne(value) {\n"
                "  const out = value + 1;\n"
                "  return out;\n"
                "}\n\n"
                "function addMany(start, increments) {\n"
                "  let total = start;\n"
                "  for (const item of increments) total += item;\n"
                "  return total;\n"
                "}\n\n"
                "module.exports = { addOne, addMany };\n"
            ),
        ]
        add_js = impls[index % len(impls)]
    else:
        bugs = [
            (
                "function addOne(value) {\n"
                "  return value;\n"
                "}\n\n"
                "function addMany(start, increments) {\n"
                "  return increments.reduce((acc, inc) => acc + inc, start);\n"
                "}\n\n"
                "module.exports = { addOne, addMany };\n"
            ),
            (
                "function addOne(value) {\n"
                "  return value + 1;\n"
                "}\n\n"
                "function addMany(start, increments) {\n"
                "  return start - increments.reduce((acc, inc) => acc + inc, 0);\n"
                "}\n\n"
                "module.exports = { addOne, addMany };\n"
            ),
            (
                "function addOne(value) {\n"
                "  return value + 2;\n"
                "}\n\n"
                "function addMany(start, increments) {\n"
                "  return increments.reduce((acc, inc) => acc + inc, start);\n"
                "}\n\n"
                "module.exports = { addOne, addMany };\n"
            ),
        ]
        add_js = bugs[index % len(bugs)]

    test = (
        "const test = require(\"node:test\");\n"
        "const assert = require(\"node:assert/strict\");\n"
        "const { addOne, addMany } = require(\"../src/ops/add\");\n\n"
        "test(\"addOne increments\", () => {\n"
        "  assert.equal(addOne(9), 10);\n"
        "  assert.equal(addOne(-4), -3);\n"
        "});\n\n"
        "test(\"addMany sums list\", () => {\n"
        "  assert.equal(addMany(3, [1, 2, 3]), 9);\n"
        "  assert.equal(addMany(0, [5, -2, -1]), 2);\n"
        "});\n"
    )

    return {
        "packages/calculator/src/ops/add.js": add_js,
        "packages/calculator/tests/add.test.js": test,
    }


def tsconfig(include_glob: str) -> str:
    return (
        "{\n"
        "  \"compilerOptions\": {\n"
        "    \"target\": \"ES2020\",\n"
        "    \"module\": \"NodeNext\",\n"
        "    \"moduleResolution\": \"NodeNext\",\n"
        "    \"rootDir\": \".\",\n"
        "    \"strict\": true,\n"
        "    \"esModuleInterop\": true,\n"
        "    \"forceConsistentCasingInFileNames\": true,\n"
        "    \"skipLibCheck\": true\n"
        "  },\n"
        f"  \"include\": [\"{include_glob}\"]\n"
        "}\n"
    )


def node_shims() -> str:
    return (
        'declare module "node:test" {\n'
        "  const test: any;\n"
        "  export default test;\n"
        "}\n\n"
        'declare module "node:assert/strict" {\n'
        "  const assert: any;\n"
        "  export default assert;\n"
        "}\n"
    )


def ts_simple_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            "export function addOne(value: number): number {\n  return value + 1;\n}\n",
            "export const addOne = (value: number): number => value + 1;\n",
            "export function addOne(value: number): number {\n  const nextValue = value + 1;\n  return nextValue;\n}\n",
        ]
        solution = impls[index % len(impls)]
    else:
        bugs = [
            "export function addOne(value: number): number {\n  return value;\n}\n",
            "export function addOne(value: number): number {\n  return value - 1;\n}\n",
            "export function addOne(value: number): number {\n  return Math.abs(value) + 1;\n}\n",
        ]
        solution = bugs[index % len(bugs)]

    test = (
        "import test from \"node:test\";\n"
        "import assert from \"node:assert/strict\";\n"
        "import { addOne } from \"./solution.js\";\n\n"
        "test(\"addOne increments values\", () => {\n"
        "  assert.equal(addOne(0), 1);\n"
        "  assert.equal(addOne(10), 11);\n"
        "  assert.equal(addOne(-1), 0);\n"
        "});\n"
    )

    return {
        "solution.ts": solution,
        "test_solution.test.ts": test,
        "tsconfig.json": tsconfig("**/*.ts"),
        "node-shims.d.ts": node_shims(),
    }


def ts_complex_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            (
                "export function add(value: number, step = 1): number {\n"
                "  return value + step;\n"
                "}\n\n"
                "export function addMany(start: number, deltas: number[]): number {\n"
                "  return deltas.reduce((acc, item) => add(acc, item), start);\n"
                "}\n"
            ),
            (
                "export function add(value: number, step = 1): number {\n"
                "  const nextValue = value + step;\n"
                "  return nextValue;\n"
                "}\n\n"
                "export function addMany(start: number, deltas: number[]): number {\n"
                "  let total = start;\n"
                "  for (const delta of deltas) total = add(total, delta);\n"
                "  return total;\n"
                "}\n"
            ),
        ]
        add_ts = impls[index % len(impls)]
    else:
        bugs = [
            (
                "export function add(value: number, step = 1): number {\n"
                "  return value - step;\n"
                "}\n\n"
                "export function addMany(start: number, deltas: number[]): number {\n"
                "  return deltas.reduce((acc, item) => add(acc, item), start);\n"
                "}\n"
            ),
            (
                "export function add(value: number, step = 1): number {\n"
                "  return value + step + 1;\n"
                "}\n\n"
                "export function addMany(start: number, deltas: number[]): number {\n"
                "  return deltas.reduce((acc, item) => acc + item, start);\n"
                "}\n"
            ),
            (
                "export function add(value: number, step = 1): number {\n"
                "  return value + step;\n"
                "}\n\n"
                "export function addMany(start: number, deltas: number[]): number {\n"
                "  return start;\n"
                "}\n"
            ),
        ]
        add_ts = bugs[index % len(bugs)]

    test = (
        "import test from \"node:test\";\n"
        "import assert from \"node:assert/strict\";\n"
        "import { add, addMany } from \"../src/index.js\";\n\n"
        "test(\"add default and custom step\", () => {\n"
        "  assert.equal(add(7), 8);\n"
        "  assert.equal(add(3, 4), 7);\n"
        "});\n\n"
        "test(\"addMany handles sequences\", () => {\n"
        "  assert.equal(addMany(1, [2, 3, 4]), 10);\n"
        "  assert.equal(addMany(10, [5, -3, -2]), 10);\n"
        "});\n"
    )

    return {
        "src/math/add.ts": add_ts,
        "src/index.ts": 'export { add, addMany } from "./math/add.js";\n',
        "tests/math_ops.test.ts": test,
        "tsconfig.json": tsconfig("**/*.ts"),
        "node-shims.d.ts": node_shims(),
    }


def ts_nested_files(index: int, passed: bool) -> dict[str, str]:
    if passed:
        impls = [
            (
                "export function addOne(value: number): number {\n"
                "  return value + 1;\n"
                "}\n\n"
                "export function addMany(start: number, increments: number[]): number {\n"
                "  return increments.reduce((acc, item) => acc + item, start);\n"
                "}\n"
            ),
            (
                "export function addOne(value: number): number {\n"
                "  const nextValue = value + 1;\n"
                "  return nextValue;\n"
                "}\n\n"
                "export function addMany(start: number, increments: number[]): number {\n"
                "  let total = start;\n"
                "  for (const inc of increments) total += inc;\n"
                "  return total;\n"
                "}\n"
            ),
        ]
        add_ts = impls[index % len(impls)]
    else:
        bugs = [
            (
                "export function addOne(value: number): number {\n"
                "  return value;\n"
                "}\n\n"
                "export function addMany(start: number, increments: number[]): number {\n"
                "  return increments.reduce((acc, item) => acc + item, start);\n"
                "}\n"
            ),
            (
                "export function addOne(value: number): number {\n"
                "  return value + 1;\n"
                "}\n\n"
                "export function addMany(start: number, increments: number[]): number {\n"
                "  return start - increments.reduce((acc, item) => acc + item, 0);\n"
                "}\n"
            ),
            (
                "export function addOne(value: number): number {\n"
                "  return value + 2;\n"
                "}\n\n"
                "export function addMany(start: number, increments: number[]): number {\n"
                "  return increments.reduce((acc, item) => acc + item, start);\n"
                "}\n"
            ),
        ]
        add_ts = bugs[index % len(bugs)]

    test = (
        "import test from \"node:test\";\n"
        "import assert from \"node:assert/strict\";\n"
        "import { addOne, addMany } from \"../src/ops/add.js\";\n\n"
        "test(\"addOne increments\", () => {\n"
        "  assert.equal(addOne(9), 10);\n"
        "  assert.equal(addOne(-4), -3);\n"
        "});\n\n"
        "test(\"addMany sums list\", () => {\n"
        "  assert.equal(addMany(3, [1, 2, 3]), 9);\n"
        "  assert.equal(addMany(0, [5, -2, -1]), 2);\n"
        "});\n"
    )

    return {
        "packages/calculator/src/ops/add.ts": add_ts,
        "packages/calculator/tests/add.test.ts": test,
        "tsconfig.json": tsconfig("**/*.ts"),
        "node-shims.d.ts": node_shims(),
    }


def file_factory(spec: Spec, index: int, passed: bool) -> dict[str, str]:
    key = (spec.language, spec.variant)
    mapping = {
        ("python", "simple"): python_simple_files,
        ("python", "complex"): python_complex_files,
        ("python", "nested"): python_nested_files,
        ("javascript", "simple"): js_simple_files,
        ("javascript", "complex"): js_complex_files,
        ("javascript", "nested"): js_nested_files,
        ("typescript", "simple"): ts_simple_files,
        ("typescript", "complex"): ts_complex_files,
        ("typescript", "nested"): ts_nested_files,
    }
    return mapping[key](index, passed)


def config_yaml(spec: Spec, candidates_name: str, experiment_id: str) -> str:
    image_by_language = {
        "python": "coderoll-python:3.11",
        "javascript": "coderoll-node:20",
        "typescript": "coderoll-node-ts:20",
    }
    timeout = spec.timeout

    if spec.language == "python":
        eval_block = (
            "eval:\n"
            "  commands:\n"
            f"    - name: tests\n"
            f"      command: python -m pytest -q {spec.test_path} --junitxml=.coderoll-results.xml\n"
            "      result_format: junit\n\n"
        )
    elif spec.language == "javascript":
        eval_block = (
            "eval:\n"
            "  commands:\n"
            f"    - name: tests\n"
            f"      command: node --test --test-reporter=tap {spec.test_path}\n"
            "      result_format: tap\n\n"
        )
    else:
        test_js_path = spec.test_path.replace(".ts", ".js")
        eval_block = (
            "eval:\n"
            "  commands:\n"
            "    - name: typecheck\n"
            "      command: tsc --noEmit\n"
            "      result_format: exit_code\n"
            "    - name: build\n"
            "      command: tsc --outDir dist\n"
            "      result_format: exit_code\n"
            "    - name: tests\n"
            f"      command: node --test --test-reporter=tap dist/{test_js_path}\n"
            "      result_format: tap\n\n"
        )

    return (
        f"id: {experiment_id}\n"
        "mode: file\n"
        f"language: {spec.language}\n\n"
        "candidates:\n"
        f"  path: {candidates_name}\n"
        "  type: jsonl\n\n"
        "setup:\n"
        "  commands: []\n\n"
        f"{eval_block}"
        "output:\n"
        f"  path: runs/{experiment_id}_results.jsonl\n\n"
        "runner:\n"
        "  workers: 6\n\n"
        "sandbox:\n"
        f"  image: {image_by_language[spec.language]}\n"
        f"  timeout: {timeout}\n"
        "  memory: 512m\n"
        "  cpus: \"1\"\n"
        "  pids_limit: 128\n"
        "  network: false\n\n"
        "viewer:\n"
        "  enabled: true\n"
        f"  out: runs/{experiment_id}.viewer.html\n"
        "  open: false\n"
    )


def generate(spec: Spec) -> None:
    spec.base_dir.mkdir(parents=True, exist_ok=True)

    candidates_path = spec.base_dir / "candidates_100.jsonl"
    experiment_id = f"{spec.language}_{spec.variant}_file_mode_100"
    config_path = spec.base_dir / "experiment_100.yaml"

    with candidates_path.open("w", encoding="utf-8") as handle:
        for idx in range(PASS_COUNT):
            files = file_factory(spec, idx, passed=True)
            row = {
                "id": f"pass_{idx + 1:03d}",
                "files": files,
                "source": "synthetic",
                "metadata": {
                    "expected": "pass",
                    "group": "pass",
                    "language": spec.language,
                    "variant": spec.variant,
                },
            }
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")

        for idx in range(FAIL_COUNT):
            files = file_factory(spec, idx, passed=False)
            row = {
                "id": f"fail_{idx + 1:03d}",
                "files": files,
                "source": "synthetic",
                "metadata": {
                    "expected": "fail",
                    "group": "fail",
                    "language": spec.language,
                    "variant": spec.variant,
                },
            }
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")

    config_path.write_text(
        config_yaml(spec, candidates_path.name, experiment_id),
        encoding="utf-8",
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    specs = [
        Spec("python", "simple", root / "python/project/simple", "test_solution.py", 20),
        Spec("python", "complex", root / "python/project/complex", "tests/test_math_ops.py", 20),
        Spec("python", "nested", root / "python/project/nested", "tests/unit/test_addition.py", 20),
        Spec("javascript", "simple", root / "js/project/simple", "test_solution.test.js", 20),
        Spec("javascript", "complex", root / "js/project/complex", "test/math_ops.test.js", 20),
        Spec(
            "javascript",
            "nested",
            root / "js/project/nested",
            "packages/calculator/tests/add.test.js",
            20,
        ),
        Spec("typescript", "simple", root / "ts/project/simple", "test_solution.test.ts", 30),
        Spec("typescript", "complex", root / "ts/project/complex", "tests/math_ops.test.ts", 30),
        Spec(
            "typescript",
            "nested",
            root / "ts/project/nested",
            "packages/calculator/tests/add.test.ts",
            30,
        ),
    ]

    for spec in specs:
        generate(spec)
        print(f"Generated: {spec.base_dir}")


if __name__ == "__main__":
    main()
