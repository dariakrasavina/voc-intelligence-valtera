# Databricks notebook source
# MAGIC %md
# MAGIC # 50 · Serve the escalation queue from Lakebase
# MAGIC `gold_escalation_queue` (Delta, CDF on) is synced into **Lakebase Postgres** as
# MAGIC `voc_valtera.lb_escalation_queue` (TRIGGERED synced table). The case-management app reads it with
# MAGIC millisecond latency and writes case status / assignee / notes into its own Lakebase schema
# MAGIC (`case_mgmt.case_actions`). This task triggers the incremental sync after each gold refresh.

# COMMAND ----------
# MAGIC %pip install -q "psycopg[binary]>=3.1"
# MAGIC %restart_python

# COMMAND ----------
import json, os, time
from databricks.sdk import WorkspaceClient
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera", "lakebase_project": "valtera-voc", "app_name": "valtera-voc-app",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, proj, ev, app_name = (dbutils.widgets.get(k) for k in ["catalog", "schema", "lakebase_project", "evidence_path", "app_name"])
w = WorkspaceClient()
SYNCED = f"{cat}.{sch}.lb_escalation_queue"
API = f"/api/2.0/postgres/synced_tables/{SYNCED}"

SPEC = {"spec": {
    "source_table_full_name": f"{cat}.{sch}.gold_escalation_queue", "primary_key_columns": ["case_id"],
    "scheduling_policy": "TRIGGERED", "branch": f"projects/{proj}/branches/production",
    "postgres_database": "databricks_postgres", "create_database_objects_if_missing": True}}

def get_synced():
    try:
        return w.api_client.do("GET", API)
    except Exception:
        return None

def create_synced():
    w.api_client.do("POST", "/api/2.0/postgres/synced_tables", query={"synced_table_id": SYNCED}, body=SPEC)
    for _ in range(60):
        time.sleep(10)
        st = get_synced()
        if st and find_pipeline_id(st):
            return st
    raise RuntimeError("synced table was not created in time")

def find_pipeline_id(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "pipeline_id" and v: return v
            r = find_pipeline_id(v)
            if r: return r
    return None

from databricks.sdk.errors import ResourceConflict

def run_sync(pid):
    try:
        update_id = w.pipelines.start_update(pipeline_id=pid).update_id
    except ResourceConflict:  # a sync is already running (e.g. the initial sync right after creation): wait for it
        update_id = w.pipelines.get(pipeline_id=pid).latest_updates[0].update_id
        print("sync already in progress, waiting for", update_id)
    for _ in range(120):
        u = w.pipelines.get_update(pipeline_id=pid, update_id=update_id).update
        if u.state.value in ("COMPLETED", "FAILED", "CANCELED"):
            return u.state.value, update_id
        time.sleep(10)
    return "TIMEOUT", update_id

st = get_synced() or create_synced()
pid = find_pipeline_id(st)
print("sync pipeline:", pid)
state, update_id = run_sync(pid)
recreated = False
if state != "COMPLETED":
    # The synced table is a read-only copy of gold: if its change-feed checkpoint no longer matches the source
    # (e.g. the source was replaced), recreate it. App-owned data lives in case_mgmt and is not affected.
    print(f"incremental sync {update_id} ended {state}; recreating the synced table")
    w.api_client.do("DELETE", API)
    for _ in range(30):
        time.sleep(10)
        if get_synced() is None: break
    st = create_synced()
    pid = find_pipeline_id(st)
    state, update_id = run_sync(pid)
    recreated = True
print("sync update:", update_id, state)

# Keep the app's read access on the synced schema (a recreated synced table gets a new owner role, so
# grants must be re-applied). Idempotent; skipped if the app is not deployed yet.
def grant_app_read():
    import psycopg
    try:
        sp = w.apps.get(app_name).service_principal_client_id
    except Exception as e:
        return f"skipped ({str(e)[:80]})"
    ep_name = f"projects/{proj}/branches/production/endpoints/primary"
    host = w.api_client.do("GET", f"/api/2.0/postgres/{ep_name}")["status"]["hosts"]["host"]
    token = w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": ep_name})["token"]
    user = w.current_user.me().user_name
    with psycopg.connect(host=host, dbname="databricks_postgres", user=user, password=token, sslmode="require") as conn:
        conn.execute(f'GRANT USAGE ON SCHEMA {sch} TO "{sp}"')
        conn.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA {sch} TO "{sp}"')
        ok = conn.execute(f"SELECT has_table_privilege('{sp}', '{sch}.lb_escalation_queue', 'SELECT')").fetchone()[0]
    return f"granted to {sp}: can_read={ok}"

app_grant = grant_app_read()
print("app access:", app_grant)

src = spark.sql(f"SELECT count(*) c FROM {cat}.{sch}.gold_escalation_queue").first().c
dst = None
for _ in range(12):  # the Postgres table is read through UC federation; allow a few seconds to settle
    try:
        dst = spark.sql(f"SELECT count(*) c FROM {SYNCED}").first().c
    except Exception as e:
        dst = f"n/a ({str(e)[:80]})"
    if dst == src: break
    time.sleep(10)
print(f"gold_escalation_queue rows: {src} | Lakebase lb_escalation_queue rows: {dst}")
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/50_lakebase_sync.json", "w") as f:
    json.dump({"synced_table": SYNCED, "lakebase_project": proj, "postgres_table": f"{sch}.lb_escalation_queue",
               "scheduling_policy": "TRIGGERED", "sync_pipeline_id": pid, "sync_update_id": update_id,
               "sync_state": state, "recreated_synced_table": recreated, "app_access": app_grant,
               "source_rows": src, "lakebase_rows": dst}, f, indent=2, default=str)
if state != "COMPLETED" or src != dst:
    raise RuntimeError(f"Lakebase sync check failed: state={state}, source={src}, lakebase={dst}")
