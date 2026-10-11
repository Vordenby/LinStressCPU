#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ARGS_FILE="$SCRIPT_DIR/CLI-Args.txt"

if [[ ! -f "$ARGS_FILE" ]]; then
    printf 'Arguments file not found: %s\n' "$ARGS_FILE" >&2
    exit 1
fi

args=()
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "${line//[[:space:]]/}" || "$line" == \#* ]] && continue
    read -r -a line_args <<< "$line"
    args+=("${line_args[@]}")
done < "$ARGS_FILE"

exec python3 "$SCRIPT_DIR/src/LinStress.py" "${args[@]}"
