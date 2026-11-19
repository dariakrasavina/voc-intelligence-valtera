# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Land the contact-center + survey export
# MAGIC Writes the **synthetic** Valtera Motors export (calls, surveys, CRM, vehicles, dealers) into the
# MAGIC `landing` UC volume, the same shape a real vendor export would arrive in.
# MAGIC `generate_mode=backfill` lands 90 days; `daily` lands one new day (incremental demo).
# MAGIC Ground-truth labels are written to a separate table used **only** for evaluation.

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
# Ground truth -> evaluation-only table (never read by any model).
ns = f'{P["catalog"]}.{P["schema"]}'
(spark.read.json(f'{P["landing_path"]}/_ground_truth/')
      .write.mode("overwrite").option("overwriteSchema", "true")
      .saveAsTable(f"{ns}.eval_ground_truth_labels"))
files = {d: len(os.listdir(os.path.join(P["landing_path"], d))) for d in ["interactions", "customers", "vehicles", "dealers"]}
print("files in landing:", files)
os.makedirs(P["evidence_path"], exist_ok=True)
with open(f'{P["evidence_path"]}/00_land_export.json', "w") as f:
    json.dump({"generator_summary": summary, "landing_files": files}, f, indent=2)
