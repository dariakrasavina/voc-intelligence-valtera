# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Rule-engine topic tagging (deterministic, explainable)
# MAGIC Runs `src/classification/rule_tag_job.py`: the rule engine (`rule_engine.py` + `tagger.py`) applied to every
# MAGIC customer sentence through a vectorized **PySpark `pandas_udf`** (ported from an earlier VOC project of mine).
# MAGIC The rules are **data** (`category_model.json`), so business users change keywords without code changes.
# MAGIC Output `sentence_rule_tags` has one row per (sentence, topic) with the **sentence text** and the words
# MAGIC that triggered the tag.

# COMMAND ----------
import json, os, sys
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
ns = f"{cat}.{sch}"

# The bundle uploads src/ next to this notebook: make the classification modules importable.
CLS = os.path.abspath("../classification")
if CLS not in sys.path:
    sys.path.insert(0, CLS)
import rule_tag_job

summary = rule_tag_job.run(spark, ns, rules_path=os.path.join(CLS, "category_model.json"))

# COMMAND ----------
freq = spark.sql(f"""SELECT topic_name, parent_topic, sentences_tagged, interactions_tagged
                     FROM {ns}.rule_tag_frequencies WHERE is_leaf ORDER BY sentences_tagged DESC""").toPandas()
examples = spark.sql(f"""SELECT topic_name, sentence_text, matched_terms FROM {ns}.sentence_rule_tags
                         WHERE via = 'direct' ORDER BY rand(3) LIMIT 8""").toPandas()
print(freq.to_string(index=False)); print(); print(examples.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/02_rule_tagging.json", "w") as f:
    json.dump({**summary, "tags_by_topic": freq.to_dict("records"), "example_explanations": examples.to_dict("records")},
              f, indent=2, default=str)
