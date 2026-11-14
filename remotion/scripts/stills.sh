#!/usr/bin/env bash
# Gera quadros de um fixture e monta uma folha de contato para revisão visual.
# Uso: scripts/stills.sh <Fixture> <quadro> [<quadro> ...]
set -euo pipefail
cd "$(dirname "$0")/.."
name="$1"; shift
mkdir -p out/stills
if [ ! -d out/bundle ] || [ -n "${REBUNDLE:-}" ]; then
  npx remotion bundle src/index.ts --out-dir=out/bundle --public-dir=fixtures/public >out/stills/log.txt 2>&1
fi
inputs=()
for f in "$@"; do
  npx remotion still out/bundle Commercial "out/stills/$name-$f.png" \
    --props="fixtures/$name.json" --frame="$f" --scale=0.5 >>out/stills/log.txt 2>&1
  inputs+=(-i "out/stills/$name-$f.png")
done
ffmpeg -v error -y "${inputs[@]}" -filter_complex "hstack=inputs=$#" "out/stills/$name-sheet.png"
echo "out/stills/$name-sheet.png"
