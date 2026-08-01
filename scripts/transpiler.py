"""
CLI: transpile a .py file matching the fixed pattern into C source.

Usage:
    python -m transpiler.cli input.py -o output.c --iterations 100 [--bits '{"h1_mul_x1": true}']
"""

from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path

from transpiler.transpiler.parser import parse_source
from transpiler.transpiler.emitter import emit_c_source
from transpiler.transpiler.schema import UnsupportedPattern

# runtime/ is always a sibling of the transpiler/ package (project root),
# regardless of where the CLI is invoked from.
RUNTIME_DIR = Path(__file__).resolve().parent / "transpiler" / "runtime"
RUNTIME_HEADERS = ("approx.h", "common.h")


def _copy_runtime_headers(output_dir: Path) -> None:
    """Copies approx.h and common.h into output_dir, since generated code
    always #includes both -- skips a header if it's already present and
    byte-identical, to avoid needless rewrites when transpiling many
    candidates into the same output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_HEADERS:
        src = RUNTIME_DIR / name
        if not src.exists():
            print(f"warning: runtime header not found at {src}, skipping", file=sys.stderr)
            continue
        dst = output_dir / name
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            continue
        shutil.copyfile(src, dst)
        print(f"copied {src} -> {dst}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="source .py file")
    ap.add_argument("-o", "--output", help="output .c file (default: stdout)")
    ap.add_argument("--bits", default="{}", help="JSON dict of op_name -> true/false (approx/exact)")
    ap.add_argument("--iterations", type=int, default=1000,
                     help="value baked in for the iterations/n parameter (default: 1000)")
    ap.add_argument("--no-runtime-headers", action="store_true",
                     help="don't copy approx.h/common.h alongside the output file")
    args = ap.parse_args(argv)

    with open(args.input, "r") as f:
        source = f.read()

    try:
        bits = json.loads(args.bits)
    except json.JSONDecodeError as e:
        print(f"error: --bits is not valid JSON: {e}", file=sys.stderr)
        return 1

    try:
        ir, helpers = parse_source(source, filename=args.input)
        c_source = emit_c_source(ir, helpers, bits=bits, iterations=args.iterations)
    except UnsupportedPattern as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(c_source)
        print(f"wrote {output_path}", file=sys.stderr)

        if not args.no_runtime_headers:
            _copy_runtime_headers(output_path.parent if output_path.parent != Path("") else Path("."))
    else:
        print(c_source)

    return 0


if __name__ == "__main__":
    sys.exit(main())