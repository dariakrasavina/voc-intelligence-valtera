# Databricks notebook source
# MAGIC %md
# MAGIC # 60 · Evaluation: rules vs. ai_classify vs. consensus (against ground truth)
# MAGIC The synthetic generator recorded the true topic of every complaint sentence (and whether it was
# MAGIC phrased with the "expected" vocabulary or as a paraphrase). That lets us measure, not guess:
# MAGIC precision / recall / F1 per method, per phrasing style and per topic.

# COMMAND ----------
import json, os
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
ns = f"{cat}.{sch}"

spark.sql(f"""CREATE OR REPLACE TEMP VIEW truth AS
  SELECT DISTINCT s.sentence_id, g.topic_id, g.variant
  FROM {ns}.eval_ground_truth_labels g
  JOIN {ns}.silver_sentences s ON s.interaction_id = g.interaction_id AND s.speaker = 'customer'
   AND (s.sentence_text = g.sentence OR endswith(s.sentence_text, concat(' ', g.sentence)))  -- surveys prefix 'Overall:' / 'Comments:'""")
spark.sql(f"""CREATE OR REPLACE TEMP VIEW preds AS
  SELECT DISTINCT sentence_id, topic_id, 'rules' AS method FROM {ns}.gold_sentence_topics WHERE detected_by IN ('rules','both')
  UNION ALL SELECT DISTINCT sentence_id, topic_id, 'ai_classify' FROM {ns}.gold_sentence_topics WHERE detected_by IN ('ai','both')
  UNION ALL SELECT DISTINCT sentence_id, topic_id, 'consensus (rules OR ai)' FROM {ns}.gold_sentence_topics""")

overall = spark.sql("""
WITH m AS (SELECT DISTINCT method FROM preds),
j AS (
  SELECT m.method,
         (SELECT count(*) FROM preds p JOIN truth t USING (sentence_id, topic_id) WHERE p.method = m.method) AS tp,
         (SELECT count(*) FROM preds p WHERE p.method = m.method) AS predicted,
         (SELECT count(*) FROM truth) AS actual
  FROM m)
SELECT method, tp, predicted - tp AS fp, actual - tp AS fn,
       round(tp / predicted, 3) AS precision, round(tp / actual, 3) AS recall,
       round(2 * tp / (predicted + actual), 3) AS f1
FROM j ORDER BY f1 DESC""").toPandas()

by_variant = spark.sql("""
SELECT m.method, t.variant, count(*) AS actual, count(p.topic_id) AS found, round(count(p.topic_id) / count(*), 3) AS recall
FROM truth t CROSS JOIN (SELECT DISTINCT method FROM preds) m
LEFT JOIN preds p ON p.sentence_id = t.sentence_id AND p.topic_id = t.topic_id AND p.method = m.method
GROUP BY ALL ORDER BY 2, 1""").toPandas()

by_topic = spark.sql(f"""
SELECT d.topic_name, m.method, count(*) AS actual, round(count(p.topic_id) / count(*), 3) AS recall
FROM truth t JOIN {ns}.dim_topics d USING (topic_id) CROSS JOIN (SELECT DISTINCT method FROM preds) m
LEFT JOIN preds p ON p.sentence_id = t.sentence_id AND p.topic_id = t.topic_id AND p.method = m.method
GROUP BY ALL ORDER BY 1, 2""").toPandas()

print("OVERALL (sentence x topic):"); print(overall.to_string(index=False))
print("\nRECALL BY PHRASING STYLE:"); print(by_variant.to_string(index=False))
print("\nRECALL BY TOPIC:"); print(by_topic.pivot(index="topic_name", columns="method", values="recall").to_string())

# COMMAND ----------
spark.createDataFrame(overall).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{ns}.eval_classification_metrics")
alerts = spark.sql(f"SELECT topic_name, model, model_year, first_alert_date, peak_lift, last_7d FROM {ns}.gold_emerging_issues WHERE is_alert ORDER BY first_alert_date").toPandas()
first_detect = spark.sql(f"""
  SELECT topic_name, model, model_year, first_alert_date, datediff(first_alert_date, DATE'2026-10-28') AS days_after_ota_42, peak_lift
  FROM {ns}.gold_emerging_issues WHERE model = 'Aurora EV' AND model_year = 2026 AND first_alert_date IS NOT NULL
  ORDER BY first_alert_date""").toPandas()
print("\nSeeded OTA 4.2 issue (shipped 2026-10-28): first alert per topic for the 2026 Aurora EV:"); print(first_detect.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/60_evaluate.json", "w") as f:
    json.dump({"overall": overall.to_dict("records"), "recall_by_phrasing": by_variant.to_dict("records"),
               "recall_by_topic": by_topic.to_dict("records"), "emerging_issue_alerts": alerts.to_dict("records"),
               "ota_42_first_detection": first_detect.to_dict("records")}, f, indent=2, default=str)
