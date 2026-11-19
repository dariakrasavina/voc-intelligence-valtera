#!/usr/bin/env bash
# Ask the Valtera VOC Genie Agent a set of business questions and save answers + generated SQL as text.
# Usage: scripts/genie_evidence.sh <profile> <space_id>
set -euo pipefail
P=${1:?profile}; SPACE=${2:?space id}
cd "$(dirname "$0")/.."; mkdir -p evidence/genie
OUT=evidence/genie/genie_conversations.md
echo "# Genie Agent answers (space $SPACE, captured $(date -u +%Y-%m-%dT%H:%MZ))" > $OUT
while IFS= read -r Q; do
  [ -z "$Q" ] && continue
  J=$(databricks genie start-conversation "$SPACE" "$Q" --profile "$P" -o json 2>&1 || true)
  echo "$J" | python3 scripts/format_genie_answer.py "$Q" >> $OUT
done <<'QS'
Which issues are spiking right now?
When was the charge port door problem on the 2026 Aurora EV first detected?
Top complaint topics for EV owners in the last 30 days
How many open P1 cases are there by topic?
Which dealers have the highest share of negative interactions?
QS
echo "wrote $OUT"
