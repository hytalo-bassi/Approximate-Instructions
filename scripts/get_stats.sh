#!/usr/bin/env bash
###
### Extracts specified options from gem5 stats.txt files and saves them as joined CSVs.
###
### Usage: ./get_stats.sh [OPTIONS] <stat1> [stat2 ...]
###
### Options:
###   -r, --recursive       Recursively search for stats.txt under the given path
###   -p, --path <dir>      Root path to search (default: current directory)
###   -d, --depth <n>       Group CSVs by folder depth relative to root (default: 1)
###   -h, --help            Show this help message
###
### Each CSV contains one row per stats.txt found under that group folder,
### with a leading "path" column showing the relative path to the stats.txt.
###
### Example:
###   ./get_stats.sh -r -p multiple_adds_example -d 2 simSeconds system.cpu.ipc
###   Groups by the first 2 folder levels, e.g.:
###     multiple_adds_example/approximate/AtomicSimpleCPU -> approximate_atomicsimplecpu.csv

set -euo pipefail

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    echo "Usage: $0 [-r] [-p <dir>] [-d <depth>] <stat1> [stat2 ...]"
    echo ""
    echo "  -r, --recursive       Recursively search for stats.txt."
    echo "  -p, --path <dir>      Root path to search (default: current directory)."
    echo "  -d, --depth <n>       Folder depth used to group CSVs (default: 1)."
    echo "  -h, --help            Show this help message."
    echo ""
    echo "  stat1, stat2 ...      Stat names to extract (e.g. simSeconds system.cpu.ipc)."
    exit 1
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
RECURSIVE=false
ROOT_PATH="."
GROUP_DEPTH=1
STATS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--recursive)
            RECURSIVE=true
            shift
            ;;
        -p|--path)
            [[ -z "${2:-}" ]] && { echo "Error: --path requires an argument." >&2; usage; }
            ROOT_PATH="$2"
            shift 2
            ;;
        -d|--depth)
            [[ -z "${2:-}" ]] && { echo "Error: --depth requires an argument." >&2; usage; }
            if ! [[ "$2" =~ ^[1-9][0-9]*$ ]]; then
                echo "Error: --depth must be a positive integer, got: '$2'" >&2
                usage
            fi
            GROUP_DEPTH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Error: Unknown option '$1'" >&2
            usage
            ;;
        *)
            STATS+=("$1")
            shift
            ;;
    esac
done

if [[ ${#STATS[@]} -eq 0 ]]; then
    echo "Error: At least one stat name must be provided." >&2
    usage
fi

if [[ ! -d "$ROOT_PATH" ]]; then
    echo "Error: Path '$ROOT_PATH' is not a directory or does not exist." >&2
    exit 1
fi

ROOT_PATH="${ROOT_PATH%/}"

# ---------------------------------------------------------------------------
# Find stats.txt files
# ---------------------------------------------------------------------------
mapfile -t STATS_FILES < <(
    if $RECURSIVE; then
        find "$ROOT_PATH" -type f -name "stats.txt" | sort
    else
        find "$ROOT_PATH" -maxdepth 1 -type f -name "stats.txt" | sort
    fi
)

if [[ ${#STATS_FILES[@]} -eq 0 ]]; then
    echo "No stats.txt files found under '$ROOT_PATH'."
    exit 0
fi

echo "Found ${#STATS_FILES[@]} stats.txt file(s)."
echo ""

# ---------------------------------------------------------------------------
# Helper: extract a single stat value from a stats.txt file
# ---------------------------------------------------------------------------
extract_stat() {
    local file="$1"
    local stat="$2"
    awk -v stat="$stat" '
        /^[[:space:]]*#/ { next }
        NF >= 2 && $1 == stat { print $2; exit }
    ' "$file"
}

# ---------------------------------------------------------------------------
# Helper: derive the group key from a stats.txt path
# Takes the first GROUP_DEPTH components of the path relative to ROOT_PATH.
# ---------------------------------------------------------------------------
derive_group_key() {
    local stats_file="$1"
    local dir
    dir="$(dirname "$stats_file")"

    # Make relative to ROOT_PATH
    local rel="${dir#"${ROOT_PATH}"/}"
    # If nothing was stripped, the file is directly in ROOT_PATH
    [[ "$rel" == "$dir" ]] && rel="."

    if [[ "$rel" == "." ]]; then
        echo "$(basename "$ROOT_PATH")"
        return
    fi

    # Split on / and take the first GROUP_DEPTH segments
    IFS='/' read -ra parts <<< "$rel"
    local depth=$(( GROUP_DEPTH < ${#parts[@]} ? GROUP_DEPTH : ${#parts[@]} ))
    local key
    key="$(IFS='/'; echo "${parts[*]:0:$depth}")"
    echo "$key"
}

# ---------------------------------------------------------------------------
# Helper: group key -> CSV filename
# ---------------------------------------------------------------------------
group_key_to_csv() {
    echo "$(echo "$1" | tr '/' '_' | tr '[:upper:]' '[:lower:]').csv"
}

# ---------------------------------------------------------------------------
# Build a flat index file:  <group_key>\t<stats_file_path>
# This avoids associative arrays entirely.
# ---------------------------------------------------------------------------
TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

INDEX_FILE="${TMPDIR_WORK}/index.tsv"

for stats_file in "${STATS_FILES[@]}"; do
    key="$(derive_group_key "$stats_file")"
    printf '%s\t%s\n' "$key" "$stats_file" >> "$INDEX_FILE"
done

# Collect unique sorted group keys
mapfile -t GROUP_KEYS < <(cut -f1 "$INDEX_FILE" | sort -u)

echo "Grouping at depth $GROUP_DEPTH — ${#GROUP_KEYS[@]} CSV(s) will be produced."
echo ""

# ---------------------------------------------------------------------------
# For each group, write a joined CSV
# ---------------------------------------------------------------------------
total_rows=0

for key in "${GROUP_KEYS[@]}"; do
    csv_name="$(group_key_to_csv "$key")"

    # Files belonging to this group, in sorted order
    mapfile -t files < <(grep -P "^${key}\t" "$INDEX_FILE" | cut -f2 | sort)

    echo "Group: $key  (${#files[@]} run(s))"
    echo "  -> $csv_name"

    # Write CSV header: path + requested stats
    {
        printf 'path'
        for stat in "${STATS[@]}"; do
            printf ',%s' "$stat"
        done
        printf '\n'
    } > "$csv_name"

    for stats_file in "${files[@]}"; do
        # Path label relative to ROOT_PATH (strip leading root/)
        local_rel="${stats_file#"${ROOT_PATH}"/}"

        printf '%s' "$local_rel" >> "$csv_name"

        for stat in "${STATS[@]}"; do
            value="$(extract_stat "$stats_file" "$stat")"
            printf ',%s' "${value:-N/A}" >> "$csv_name"
        done

        printf '\n' >> "$csv_name"

        echo "    $local_rel"
        (( total_rows++ )) || true
    done

    echo ""
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================================"
echo "Done. $total_rows row(s) written across ${#GROUP_KEYS[@]} CSV(s)."
echo "============================================================"