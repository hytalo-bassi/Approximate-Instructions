#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory>"
    echo "This script compiles a bunch of C source files in the specified directory"
    exit 1
fi

dir="$1"

if [ ! -d "$dir" ]; then
    echo "Error: $dir is not a valid directory"
    exit 1
fi

set -e
for file in "$dir"/*.c; do
    filename=$(basename "$file" .c)
    riscv64-unknown-linux-musl-gcc -O0 -static -pthread -o "$dir/$filename" "$file" -lm || { echo "Error: Compilation failed"; exit 1; }
done
