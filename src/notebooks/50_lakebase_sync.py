# Databricks notebook source
# MAGIC %md
# MAGIC # 50 · Serve the escalation queue from Lakebase
# MAGIC `gold_escalation_queue` (Delta, CDF on) is synced into **Lakebase Postgres** as
# MAGIC `voc_valtera.lb_escalation_queue` (TRIGGERED synced table). The case-management app reads it with
# MAGIC millisecond latency and writes case status / assignee / notes into its own Lakebase schema
# MAGIC (`case_mgmt.case_actions`). This task triggers the incremental sync after each gold refresh.

# COMMAND ----------
import json, os, time
from databricks.sdk import WorkspaceClient
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera", "lakebase_project": "valtera-voc",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, proj, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "lakebase_project", "evidence_path"])
w = WorkspaceClient()
SYNCED = f"{cat}.{sch}.lb_escalation_queue"
API = f"/api/2.0/postgres/synced_tables/{SYNCED}"

try:
    st = w.api_client.do("GET", API)
except Exception as e:  # first run: create it (idempotent bootstrap)
    print("synced table not found, creating:", str(e)[:120])
    w.api_client.do("POST", "/api/2.0/postgres/synced_tables", query={"synced_table_id": SYNCED}, body={"spec": {
        "source_table_full_name": f"{cat}.{sch}.gold_escalation_queue", "primary_key_columns": ["case_id"],
        "scheduling_policy": "TRIGGERED", "branch": f"projects/{proj}/branches/production",
        "postgres_database": "databricks_postgres", "create_database_objects_if_missing": True}})
    for _ in range(60):
        time.sleep(10)
        try:
            st = w.api_client.do("GET", API); break
        except Exception:
            pass
print(json.dumps(st.get("status", {}), indent=1, default=str)[:1500])

# COMMAND ----------
def find_pipeline_id(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "pipeline_id" and v: return v
            r = find_pipeline_id(v)
            if r: return r
    return None

pid = find_pipeline_id(st)
print("sync pipeline:", pid)
from databricks.sdk.errors import ResourceConflict

def run_sync(full_refresh=False):
    try:
        update_id = w.pipelines.start_update(pipeline_id=pid, full_refresh=full_refresh).update_id
    except ResourceConflict:  # a sync is already running (e.g. the initial sync right after creation): wait for it
        update_id = w.pipelines.get(pipeline_id=pid).latest_updates[0].update_id
        print("sync already in progress, waiting for", update_id)
    for _ in range(120):
        u = w.pipelines.get_update(pipeline_id=pid, update_id=update_id).update
        if u.state.value in ("COMPLETED", "FAILED", "CANCELED"):
            return u.state.value, update_id
        time.sleep(10)
    return "TIMEOUT", update_id

state, update_id = run_sync()
recovered = False
if state != "COMPLETED":
    # e.g. the source table was replaced and the change-feed checkpoint no longer matches: rebuild once.
    print(f"incremental sync {update_id} ended {state}; running a full refresh")
    state, update_id = run_sync(full_refresh=True)
    recovered = True
print("sync update:", update_id, state)

src = spark.sql(f"SELECT count(*) c FROM {cat}.{sch}.gold_escalation_queue").first().c
dst = None
for _ in range(12):  # the Postgres table is read through UC federation; allow a few seconds to settle
    dst = spark.sql(f"SELECT count(*) c FROM {SYNCED}").first().c
    if dst == src: break
    time.sleep(10)
print(f"gold_escalation_queue rows: {src} | Lakebase lb_escalation_queue rows: {dst}")
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/50_lakebase_sync.json", "w") as f:
    json.dump({"synced_table": SYNCED, "lakebase_project": proj, "postgres_table": f"{sch}.lb_escalation_queue",
               "scheduling_policy": "TRIGGERED", "sync_pipeline_id": pid, "sync_update_id": update_id,
               "sync_state": state, "recovered_with_full_refresh": recovered,
               "source_rows": src, "lakebase_rows": dst}, f, indent=2, default=str)
if state != "COMPLETED" or src != dst:
    raise RuntimeError(f"Lakebase sync check failed: state={state}, source={src}, lakebase={dst}")
