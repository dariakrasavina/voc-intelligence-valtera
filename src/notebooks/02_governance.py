# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Unity Catalog governance
# MAGIC * PII columns in `silver_customers` are **tagged** (`pii`) so they are discoverable and auditable.
# MAGIC * A masking function + `customers_secure` view expose customers to analysts, the app and Genie
# MAGIC   **without** names/emails/phones unless the reader is in the `valtera_voc_pii_readers` group.
# MAGIC * Gold tables carry no PII by design (customer_id only), so Genie and the app never need raw PII.

# COMMAND ----------
import json, os
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
ns = f"{cat}.{sch}"
log = []

def run(q, tolerate=False):
    try:
        spark.sql(q); log.append({"sql": q.strip()[:160], "ok": True})
    except Exception as e:
        if not tolerate: raise
        log.append({"sql": q.strip()[:160], "ok": False, "error": str(e)[:200]})

# COMMAND ----------
for col in ["first_name", "last_name", "email", "phone"]:
    run(f"ALTER TABLE {ns}.silver_customers ALTER COLUMN {col} SET TAGS ('pii' = '{col}')", tolerate=True)
run(f"ALTER SCHEMA {ns} SET TAGS ('domain' = 'customer_experience', 'data_class' = 'synthetic')", tolerate=True)

run(f"""CREATE OR REPLACE FUNCTION {ns}.mask_pii(v STRING)
RETURNS STRING
COMMENT 'Returns the value for members of valtera_voc_pii_readers, otherwise a masked value.'
RETURN CASE WHEN is_account_group_member('valtera_voc_pii_readers') THEN v
            WHEN v IS NULL THEN NULL
            ELSE concat(left(v, 1), repeat('*', 6)) END""")

run(f"""CREATE OR REPLACE VIEW {ns}.customers_secure
COMMENT 'Customer profile with PII masked unless the reader is in valtera_voc_pii_readers. Use this, not silver_customers.'
AS SELECT customer_id, {ns}.mask_pii(first_name) AS first_name, {ns}.mask_pii(last_name) AS last_name,
          {ns}.mask_pii(email) AS email, {ns}.mask_pii(phone) AS phone,
          state, region, loyalty_tier, updated_at
   FROM {ns}.silver_customers""")

# COMMAND ----------
display(spark.sql(f"SELECT * FROM {ns}.customers_secure LIMIT 5"))
tags = spark.sql(f"""SELECT table_name, column_name, tag_name, tag_value
                     FROM {cat}.information_schema.column_tags
                     WHERE schema_name = '{sch}' ORDER BY 1, 2""").toPandas()
print(tags.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/02_governance.json", "w") as f:
    json.dump({"statements": log, "column_tags": tags.to_dict("records"),
               "masked_sample": spark.sql(f"SELECT customer_id, first_name, email, loyalty_tier FROM {ns}.customers_secure LIMIT 3").toPandas().to_dict("records")}, f, indent=2, default=str)
