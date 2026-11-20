# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Generate and land the contact-center + survey export (simulator)
# MAGIC Writes the **synthetic** Valtera Motors export (calls, surveys, CRM, vehicles, dealers) into the
# MAGIC `landing` UC volume, the same shape a real vendor export would arrive in.
# MAGIC `generate_mode=backfill` lands 90 days; `daily` lands one new day (incremental demo).
# MAGIC Runs in its own job (`valtera-voc-export-simulator`): it plays the vendor whose export lands in the volume.
# MAGIC The landing triggers `valtera-voc-end-to-end` (file-arrival trigger). Ground-truth labels land in
# MAGIC `_ground_truth/` and are read **only** by `08_evaluate`.

# COMMAND ----------
import json, os, sys
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera",
             "landing_path": "/Volumes/daria_krasavina/voc_valtera/landing",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence",
             "generate_mode": "backfill", "day": ""}.items():
    dbutils.widgets.text(k, v)
P = {k: dbutils.widgets.get(k) for k in ["catalog", "schema", "landing_path", "evidence_path", "generate_mode", "day"]}
sys.path.insert(0, os.path.abspath("../data_gen"))
import generate_synthetic_voc as gen

# COMMAND ----------
args = ["--out", P["landing_path"], "--mode", P["generate_mode"]]
if P["generate_mode"] == "daily" and P["day"]:
    args += ["--day", P["day"]]
summary = gen.main(args)
print(json.dumps(summary, indent=2))

# COMMAND ----------
files = {d: len(os.listdir(os.path.join(P["landing_path"], d))) for d in ["interactions", "customers", "vehicles", "dealers"]}
print("files in landing:", files)
os.makedirs(P["evidence_path"], exist_ok=True)
with open(f'{P["evidence_path"]}/01_generate_export.json', "w") as f:
    json.dump({"generator_summary": summary, "landing_files": files}, f, indent=2)
