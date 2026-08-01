"""
Marker decorators used by source .py files targeted by the transpiler.

These are no-ops at Python runtime (so the original .py files still run
normally under CPython for testing/reference) but are detected by the
transpiler's AST walker to control code generation.

Usage in a source file:

    from transpile_annotations import helper

    @helper
    def _synthetic_inputs(n):
        return [(math.sin(i * 0.31), math.cos(i * 0.17)) for i in range(n)]

Marks `_synthetic_inputs` as a helper: the transpiler will translate its
body into a C function that returns a malloc'd array, and every call site
`_synthetic_inputs(iterations)` in the main function becomes a precomputed
array filled before the main loop.
"""


def helper(fn):
    """Marks a function as a transpile-time helper (precomputed array generator)."""
    fn._transpile_helper = True
    return fn
