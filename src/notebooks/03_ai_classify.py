# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · GenAI topic classification with `ai_classify` (v2.1, multi-label)
# MAGIC Runs `src/classification/ai_classify_job.py` (ported from an earlier VOC project of mine). The labels are read from
# MAGIC `category_model.json`: each topic's plain-language `ai_description`, the same file the rule engine uses.
# MAGIC ai_classify catches paraphrases the keyword rules miss ("that little door where you plug in won't budge").
# MAGIC
# MAGIC **Cost control:** one call per *distinct* customer sentence, cached by (sentence text, definitions
# MAGIC fingerprint). Re-runs with unchanged definitions cost nothing; editing any definition re-classifies.
# MAGIC Output `sentence_ai_tags` has one row per (sentence, topic) with the **sentence text**, confidence and rationale.

# COMMAND ----------
import json, os, sys
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera", "min_confidence": "0.6",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
ns = f"{cat}.{sch}"

CLS = os.path.abspath("../classification")
if CLS not in sys.path:
    sys.path.insert(0, CLS)
import ai_classify_job

summary = ai_classify_job.run(spark, ns, rules_path=os.path.join(CLS, "category_model.json"),
                              min_confidence=float(dbutils.widgets.get("min_confidence")))

# COMMAND ----------
by_topic = spark.sql(f"""SELECT topic_name, count(*) AS tagged_sentences, round(avg(confidence), 3) AS avg_confidence
                         FROM {ns}.sentence_ai_tags GROUP BY 1 ORDER BY 2 DESC""").toPandas()
examples = spark.sql(f"""SELECT topic_name, sentence_text, confidence, rationale FROM {ns}.sentence_ai_tags
                         ORDER BY rand(7) LIMIT 8""").toPandas()
print(by_topic.to_string(index=False)); print(); print(examples.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/03_ai_classify.json", "w") as f:
    json.dump({**summary, "tags_by_topic": by_topic.to_dict("records"), "examples": examples.to_dict("records")},
              f, indent=2, default=str)
