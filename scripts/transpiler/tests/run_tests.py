#!/usr/bin/env python3
"""
Minimal regression harness: transpiles the example .py files, compiles
the resulting C with gcc against the stub runtime headers, and checks
that a deliberately malformed input is rejected with UnsupportedPattern
rather than silently mis-transpiled.

Run: python3 tests/run_tests.py
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.parser import parse_source
from transpiler.emitter import emit_c_source
from transpiler.schema import UnsupportedPattern


def transpile_and_compile(py_path, bits=None, iterations=1000):
    with open(py_path) as f:
        source = f.read()
    ir, helpers = parse_source(source, filename=py_path)
    c_source = emit_c_source(ir, helpers, bits=bits or {}, iterations=iterations)

    c_path = f"/tmp/{os.path.basename(py_path)}.c"
    bin_path = f"/tmp/{os.path.basename(py_path)}.bin"
    with open(c_path, "w") as f:
        f.write(c_source)

    result = subprocess.run(
        ["gcc", "-I", os.path.join(ROOT, "runtime"), "-Wall", "-std=c99",
         "-o", bin_path, c_path, "-lm"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"COMPILE FAILED for {py_path}:\n{result.stderr}")
        return False

    run_result = subprocess.run([bin_path, "/tmp/out.json"], capture_output=True, text=True)
    if run_result.returncode != 0:
        print(f"RUNTIME FAILED for {py_path}: exit {run_result.returncode}\n{run_result.stderr}")
        return False

    print(f"OK: {py_path} transpiled, compiled, and ran cleanly")
    return True


def test_rejects_unsupported_pattern():
    bad_source = '''
def broken_main(iterations, bits):
    total = 0
    for i in range(iterations):
        total = total + i  # plain BinOp add, not an approx op -- fine
        weird = some_unknown_function(total)  # not in any rule table
    return ExecutionResult(final_value=total, history=[], execution_count={})
'''
    try:
        ir, helpers = parse_source(bad_source, filename="<test>")
        emit_c_source(ir, helpers, bits={})
        print("FAIL: expected UnsupportedPattern for unknown function call, but none raised")
        return False
    except UnsupportedPattern as e:
        print(f"OK: unsupported pattern correctly rejected ({e})")
        return True


def main():
    results = []
    results.append(transpile_and_compile(os.path.join(ROOT, "examples/nn_inference.py")))
    results.append(transpile_and_compile(
        os.path.join(ROOT, "examples/nn_inference.py"),
        bits={"h1_mul_x1": True, "out_add": True},  # exercise the approx ('x') path too
    ))
    results.append(transpile_and_compile(os.path.join(ROOT, "examples/ema.py")))
    results.append(test_rejects_unsupported_pattern())

    if all(results):
        print("\nAll tests passed.")
        return 0
    else:
        print("\nSome tests FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())