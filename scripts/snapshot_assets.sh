#!/usr/bin/env bash
# Snapshot the definition + status of every deployed asset as text, for the evidence folder.
# Usage: scripts/snapshot_assets.sh <profile>
set -euo pipefail
P=${1:?profile}
cd "$(dirname "$0")/.."; D=evidence/assets; mkdir -p $D
j() { python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps($1, indent=2, default=str))"; }

PID=$(databricks pipelines list-pipelines --filter "name LIKE 'valtera-voc-ingest'" --profile "$P" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["pipeline_id"])')
databricks pipelines get "$PID" --profile "$P" -o json | j '{"name": d["name"], "state": d.get("state"), "spec": {k: d["spec"].get(k) for k in ("catalog","schema","serverless","channel","continuous","libraries","configuration")}, "latest_updates": d.get("latest_updates", [])[:3]}' > $D/lakeflow_pipeline.json

JID=$(databricks jobs list --name valtera-voc-end-to-end --profile "$P" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["job_id"])')
databricks jobs get "$JID" --profile "$P" -o json | j '{"job_id": d["job_id"], "name": d["settings"]["name"], "trigger": d["settings"].get("trigger"), "tasks": [{"task_key": t["task_key"], "depends_on": [x["task_key"] for x in t.get("depends_on", [])], "type": [k for k in t if k.endswith("_task")]} for t in d["settings"]["tasks"]]}' > $D/lakeflow_job.json
databricks jobs list-runs --job-id "$JID" --limit 10 --profile "$P" -o json | j '[{"run_id": r["run_id"], "trigger": r.get("trigger"), "result": r["state"].get("result_state"), "start_time": r["start_time"]} for r in d]' > $D/lakeflow_job_recent_runs.json

databricks postgres get-project projects/valtera-voc --profile "$P" -o json | j '{"name": d["name"], "display_name": d.get("status",{}).get("display_name") or d.get("spec",{}).get("display_name"), "pg_version": d.get("status",{}).get("pg_version")}' > $D/lakebase_project.json
databricks postgres get-synced-table synced_tables/daria_krasavina.voc_valtera.lb_escalation_queue --profile "$P" -o json | j '{"name": d["name"], "spec": d.get("spec"), "status": {k: d.get("status",{}).get(k) for k in ("detailed_state","message","last_sync")}}' > $D/lakebase_synced_table.json
databricks postgres list-cdf-configs projects/valtera-voc/branches/production/databases/databricks-postgres --profile "$P" -o json > $D/lakehouse_sync_cdf_configs.json
databricks psql --project valtera-voc --profile "$P" -- -c "select count(*) as queue_rows from voc_valtera.lb_escalation_queue; select status, count(*) from case_mgmt.case_actions group by 1; select count(*) as audit_log_rows from case_mgmt.case_action_log; select * from wal2delta.tables;" 2>&1 | grep -v -E 'Connect|Project|Branch|Endpoint' > $D/lakebase_postgres_checks.txt

SPACE=$(python3 -c 'import json;print(json.load(open("evidence/task_outputs/08_genie_space.json"))["space_id"])')
databricks genie get-space "$SPACE" --include-serialized-space --profile "$P" -o json | j '{"space_id": d["space_id"], "title": d["title"], "description": d.get("description"), "warehouse_id": d.get("warehouse_id"), "serialized_space": json.loads(d["serialized_space"])}' > $D/genie_space.json

databricks registered-models get daria_krasavina.voc_valtera.voc_sentiment_model --include-aliases --profile "$P" -o json | j '{"full_name": d["full_name"], "aliases": d.get("aliases"), "updated_at": d.get("updated_at")}' > $D/uc_model.json
databricks apps get valtera-voc-app --profile "$P" -o json | j '{"name": d["name"], "url": d.get("url"), "app_status": d.get("app_status"), "compute_status": d.get("compute_status"), "resources": d.get("resources"), "user_api_scopes": d.get("user_api_scopes"), "active_deployment": {k: d.get("active_deployment",{}).get(k) for k in ("deployment_id","status","create_time")}}' > $D/databricks_app.json
# Landing volume: what the synthetic export put there (files, sizes, raw samples) + the generator's own summary
{
  echo "# Landing volume /Volumes/daria_krasavina/voc_valtera/landing"
  for f in interactions customers vehicles dealers _ground_truth; do
    databricks fs ls "dbfs:/Volumes/daria_krasavina/voc_valtera/landing/$f" --long --profile "$P" -o json | python3 -c "
import json,sys; fs=sorted(json.load(sys.stdin), key=lambda x: x['name'])
print('%-14s %3d files %10d bytes   first: %s   last: %s' % ('$f', len(fs), sum(x.get('size',0) for x in fs), fs[0]['name'], fs[-1]['name']))"
  done
  echo; echo "# Generator summary (deterministic, seed 42: regenerating reproduces the landed files exactly)"
  T=$(mktemp -d); python3 src/data_gen/generate_synthetic_voc.py --out "$T/b" --mode backfill; python3 src/data_gen/generate_synthetic_voc.py --out "$T/d" --mode daily --day 2026-11-20; rm -rf "$T"
  echo; echo "# Raw sample: one call transcript as landed (interactions_20261105.json, first record)"
  databricks fs cat dbfs:/Volumes/daria_krasavina/voc_valtera/landing/interactions/interactions_20261105.json --profile "$P" > /tmp/_raw_inter.json
  python3 -c "import json; print(json.dumps(json.loads(open('/tmp/_raw_inter.json').readline()), indent=2))"
  echo; echo "# Raw sample: first 5 CRM records as landed (messy on purpose; cleaned in silver_customers)"
  databricks fs cat dbfs:/Volumes/daria_krasavina/voc_valtera/landing/customers/customers_0001_initial.json --profile "$P" > /tmp/_raw_cust.json
  python3 -c "print(''.join(open('/tmp/_raw_cust.json').readlines()[:5]), end='')"
} > $D/landing_volume.txt

# Lakeflow pipeline event log: rows written and data-quality expectation results for the latest updates
databricks experimental aitools tools query "
SELECT origin.update_id, min(timestamp) AS at, origin.flow_name AS flow,
       sum(details:flow_progress.metrics.num_output_rows::bigint) AS output_rows,
       to_json(collect_list(details:flow_progress.data_quality.expectations)) AS expectations
FROM event_log('$PID') WHERE event_type = 'flow_progress' AND details:flow_progress.status = 'COMPLETED'
  AND timestamp > current_timestamp() - INTERVAL 1 DAY
GROUP BY ALL ORDER BY at DESC LIMIT 40" --warehouse 148ccb90800933a1 --profile "$P" > $D/lakeflow_pipeline_event_log.json
# Lakebase: schemas and tables created (synced queue schema + app-owned case_mgmt schema)
databricks psql --project valtera-voc --profile "$P" -- -c "\\dn" -c "SELECT table_schema, table_name, table_type FROM information_schema.tables WHERE table_schema IN ('voc_valtera','case_mgmt') ORDER BY 1,2;" 2>&1 | grep -v -E 'Connect|Project|Branch|Endpoint' > $D/lakebase_schemas_and_tables.txt

# App write-back, end to end: app -> Lakebase case_mgmt -> Lakehouse Sync -> UC history -> gold_case_status
{
  echo "# 1. Saved in the app -> Lakebase Postgres case_mgmt.case_actions (latest state) and case_action_log (audit)"
  databricks psql --project valtera-voc --profile "$P" -- -c "SELECT case_id, status, assignee, note, updated_by, updated_at FROM case_mgmt.case_actions ORDER BY updated_at DESC;" -c "SELECT id, case_id, status, assignee, updated_by, logged_at FROM case_mgmt.case_action_log ORDER BY id;" 2>&1 | grep -v -E 'Connect|Project|Branch|Endpoint'
  echo; echo "# 2. Lakehouse Sync (CDC) -> Unity Catalog daria_krasavina.voc_valtera.lb_case_actions_history"
  databricks experimental aitools tools query "SELECT _pg_change_type, case_id, status, assignee, CAST(_timestamp AS STRING) AS synced_at FROM daria_krasavina.voc_valtera.lb_case_actions_history ORDER BY _sort_by" --warehouse 148ccb90800933a1 --profile "$P"
  echo; echo "# 3. gold_case_status (what Monitoring and Genie read)"
  databricks experimental aitools tools query "SELECT case_id, priority, primary_topic, status, assignee, note, CAST(last_updated_at AS STRING) AS last_updated_at FROM daria_krasavina.voc_valtera.gold_case_status WHERE status <> 'Open' ORDER BY last_updated_at" --warehouse 148ccb90800933a1 --profile "$P"
} > evidence/app_writeback.md

# App pages, the queries each page uses, and the Genie wiring (from the deployed source)
python3 - > $D/databricks_app_pages.md <<'PY'
import re, os, json
src = open("app/client/src/App.tsx").read()
print("# Databricks App pages (app/client/src)\n\n| Route | Page | Data used |\n|---|---|---|")
for path, comp in re.findall(r"path: '([^']+)', element: <(\w+)", src):
    f = "app/client/src/pages/%s.tsx" % comp
    body = open(f).read() if os.path.exists(f) else ""
    q = sorted(set(re.findall(r"(?:queryKey=\"|useAnalyticsQuery\(')(\w+)", body)))
    extra = []
    if "/api/cases" in body: extra.append("Lakebase via /api/cases (read queue, write case actions)")
    if "useGenieChat" in body: extra.append("Genie Agent via useGenieChat (alias voc)")
    print("| `%s` | %s | %s |" % (path, comp, ", ".join(["SQL: " + x for x in q] + extra)))
d = json.load(open("evidence/assets/databricks_app.json"))
print("\n## Deployed app resources\n")
for r in d.get("resources") or []:
    print("- %s: %s" % (r["name"], json.dumps({k: v for k, v in r.items() if k != "name"})))
print("\nuser_api_scopes: %s (Genie runs on behalf of the signed-in user)" % d.get("user_api_scopes"))
PY
# Public repo: redact any personal email and free-text person names typed into the app
for f in $D/* evidence/app_writeback.md; do
  [ -f "$f" ] && python3 -c "import re,sys; p=sys.argv[1]; s=open(p).read(); s=re.sub(r'[A-Za-z0-9._%+-]+@databricks\\.com', '<redacted>', s); open(p,'w').write(s)" "$f"
done
echo "asset snapshots written to $D"
