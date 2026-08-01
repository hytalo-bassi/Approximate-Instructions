# Python -> C transpiler for approximate-computing benchmark functions

Transpiles Python functions matching a fixed pattern (main function taking
`(iterations, bits)`, calling `s_mul`/`s_add`/`s_div`/etc against a `bits`
dict, returning `ExecutionResult`) into standalone C programs using the
`common_api_*` / `approx.h` runtime.

This is a **pattern-matching transpiler, not a general Python compiler**:
anything that doesn't match a known shape raises `UnsupportedPattern` with
a line number, rather than being silently guessed at.

## Usage

```bash
# exact mode for all ops (default bits.get(..., False) behavior)
python3 -m transpiler.cli examples/nn_inference.py -o nn_inference.c

# with specific ops flagged for the approximate variant
python3 -m transpiler.cli examples/nn_inference.py -o nn_inference.c \
    --bits '{"h1_mul_x1": true, "out_add": true}'

# compile the result (against the stub runtime, or your real one)
riscv64-unknown-linux-musl-gcc -O2 -static -o nn_inference nn_inference.c -lm
```

## Project layout

- `transpiler/schema.py` — the IR (intermediate representation) that a
  recognized source file gets parsed into.
- `transpiler/rules.py` — the extensible rule tables: Python function name
  -> C function name(s), e.g. `s_mul` -> `fmul` (exact) / `fmulx` (approx).
  Add new approximable ops or plain math-call translations here.
- `transpiler/parser.py` — walks the Python AST, matches it against the
  fixed pattern, and builds the IR. Raises `UnsupportedPattern` on
  anything unrecognized.
- `transpiler/expr_emitter.py` — generic (but narrow) Python-expression ->
  C-expression translator, shared by loop bodies, metadata, and helper
  function bodies.
- `transpiler/emitter.py` — turns the IR into the final C source text.
- `transpiler/cli.py` — command-line entry point.
- `transpile_annotations.py` — the `@helper` decorator source files import
  to mark precomputable input-generator functions (e.g. synthetic input
  series). No-op at Python runtime; read by the transpiler's AST walker.
- `runtime/approx.h`, `runtime/common.h` — **stub** implementations of the
  runtime library, just enough to compile-check generated output. Replace
  with your real implementations for production builds.
- `examples/` — two working source patterns (`nn_inference.py`,
  `ema.py`) covering: multi-var loop unpacking, single-var loop, pre-loop
  seeding, module-level constant dicts, `@helper`-decorated array
  generators (including ones with extra parameters and Python defaults),
  post-loop op calls, and metadata (`string`/array-of-pairs from
  `history` or a fresh helper call).
- `tests/run_tests.py` — transpiles both examples (including with a
  non-empty `bits` dict to exercise the approx-op path), compiles the
  result with `gcc`, runs the binary, and checks that a deliberately
  malformed input is rejected rather than mis-transpiled.

## What's supported

- Main function signature `(iterations, bits, *extra_scalar_kwargs)`
- Module-level constant dicts (`_W = {...}`) -> flattened C float decls
- `@helper`-decorated functions returning `[expr for i in range(n)]` or
  `[(e1, e2) for i in range(n)]` -> malloc'd C arrays (single or parallel,
  respectively), including extra parameters with Python defaults
- `s_mul`/`s_add`/`s_sub`/`s_div` calls with `bits.get("op_name", False)`
  -> `fmul`/`fadd`/`fsub`/`fdiv` (exact) or their `x`-suffixed approx
  counterparts, chosen per-op via the `--bits` CLI flag at transpile time
- `execution_count["op"] += 1` -> `common_api_history_increment(...)`
- `history.append(x)` -> `common_api_history_push_number(...)`
- Known passthrough math calls (`math.tanh`, `math.sin`, `math.cos`, etc)
- `return ExecutionResult(final_value=..., history=..., execution_count=...,
  metadata={...})` -> the final C output boilerplate
- Metadata values: string/number/bool constants, and
  `[(i, v) for i, v in enumerate(<history var or a fresh helper call>)]`
  -> `common_api_metadata_set_*` calls

## What's NOT supported (raises `UnsupportedPattern`)

- More than one main loop, or loops not iterating a plain name / helper
  result
- Function calls not registered in `rules.py`'s `APPROX_OP_RULES` or
  `EXACT_CALL_RULES` — add a rule rather than expecting it to "just work"
- Approx-op calls nested inside larger expressions (must be a direct
  assignment statement, since the exact/approx choice needs a clear
  statement-level target)
- Arbitrary control flow (`if`/`while`/nested loops) inside the main loop
- Metadata values that aren't constants or `enumerate(...)`-shaped list
  comprehensions

## Extending

To support a new approximable op, add one line to `APPROX_OP_RULES` in
`rules.py`:

```python
"s_pow": ApproxOpRule(exact_fn="fpow"),  # -> fpow / fpowx
```

To support a new plain math call, add one line to `EXACT_CALL_RULES`:

```python
"math.atan": ExactCallRule(c_fn="atanf"),
```

Anything more structural (a new statement shape, a new metadata value
type) means extending `parser.py` (recognize it -> add an IR node in
`schema.py`) and `emitter.py` (emit C for that IR node) together.
