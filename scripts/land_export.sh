#!/usr/bin/env bash
# Plays the source system: generates the synthetic Valtera export locally and copies it into the landing volume.
# The new files start valtera-voc-end-to-end through its file-arrival trigger (about 2 minutes after the copy).
#
# Usage: scripts/land_export.sh <profile> backfill            # 90 days: 2026-08-22 .. 2026-11-19
#        scripts/land_export.sh <profile> daily YYYY-MM-DD    # one more day
set -euo pipefail
P=${1:?profile}; MODE=${2:-daily}; DAY=${3:-$(date +%F)}
LANDING=dbfs:/Volumes/daria_krasavina/voc_valtera/landing
cd "$(dirname "$0")/.."
OUT=$(mktemp -d)
if [ "$MODE" = backfill ]; then
  python3 src/data_gen/generate_synthetic_voc.py --out "$OUT" --mode backfill
else
  python3 src/data_gen/generate_synthetic_voc.py --out "$OUT" --mode daily --day "$DAY"
fi
for d in "$OUT"/*/; do
  databricks fs cp -r --overwrite "$d" "$LANDING/$(basename "$d")" --profile "$P" >/dev/null
done
echo "landed $(find "$OUT" -type f | wc -l | tr -d ' ') files into $LANDING; the file-arrival trigger will start valtera-voc-end-to-end"
rm -rf "$OUT"
