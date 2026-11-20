#!/usr/bin/env bash
# One-time access setup for the app's service principal (least privilege). Run after the first app deploy.
# Usage: scripts/setup_app_access.sh <profile>
set -euo pipefail
P=${1:?profile}; W=148ccb90800933a1; NS=daria_krasavina.voc_valtera
SP=$(databricks apps get valtera-voc-app --profile "$P" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)["service_principal_client_id"])')
q() { databricks experimental aitools tools query "$1" --warehouse $W --profile "$P" >/dev/null; echo "ok: $1"; }
# Unity Catalog: only PII-free gold objects (never silver_customers / bronze)
q "GRANT USE CATALOG ON CATALOG daria_krasavina TO \`$SP\`"
q "GRANT USE SCHEMA ON SCHEMA $NS TO \`$SP\`"
for t in gold_interaction_insights gold_topic_daily gold_emerging_issues gold_escalation_queue gold_sentence_topics gold_case_status eval_classification_metrics dim_topics mv_voc_metrics; do
  q "GRANT SELECT ON TABLE $NS.$t TO \`$SP\`"
done
# Lakebase: read the synced escalation queue (the app creates and owns its own case_mgmt schema)
databricks psql --project valtera-voc --profile "$P" -- -c "GRANT USAGE ON SCHEMA voc_valtera TO \"$SP\"; GRANT SELECT ON ALL TABLES IN SCHEMA voc_valtera TO \"$SP\"; ALTER DEFAULT PRIVILEGES IN SCHEMA voc_valtera GRANT SELECT ON TABLES TO \"$SP\";"
