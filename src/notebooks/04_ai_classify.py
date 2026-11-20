# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · GenAI topic classification with `ai_classify` (v2.1, multi-label)
# MAGIC The rule engine is precise but only catches wording it was told about. `ai_classify` reads the
# MAGIC **plain-language topic definitions** from the same `category_model.json` and catches paraphrases
# MAGIC ("that little door where you plug in won't budge").
# MAGIC
# MAGIC **Cost control:** classify each *distinct* customer sentence once, skip filler (< 4 words),
# MAGIC and cache results by text hash so re-runs and daily increments only pay for new wording.

# COMMAND ----------
import json, os, time
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera", "min_confidence": "0.6",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
min_conf = float(dbutils.widgets.get("min_confidence"))
ns = f"{cat}.{sch}"
model = json.load(open(os.path.abspath("../classification/category_model.json")))
leaves = [n for n in model["nodes"] if n["is_leaf"]]
LABELS = json.dumps({n["name"]: n["ai_description"][:1000] for n in leaves})
INSTRUCTIONS = ("You label one sentence a customer said to an automaker's contact center or wrote in a "
                "post-service survey. Assign a topic ONLY when the sentence clearly expresses it. Most "
                "sentences match nothing: return no labels for greetings, small talk, acknowledgments, "
                "vehicle descriptions without a problem, and generic questions.")
spark.createDataFrame([(n["id"], n["name"], n["path"][-1], n["escalation_weight"]) for n in leaves],
                      "topic_id string, topic_name string, parent_topic string, escalation_weight int") \
     .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{ns}.dim_topics")

# COMMAND ----------
spark.sql(f"""CREATE TABLE IF NOT EXISTS {ns}.ai_classify_cache (
  text_hash STRING, sentence_text STRING, ai_result STRING, classified_at TIMESTAMP)
  COMMENT 'One ai_classify call per distinct customer sentence; re-used across runs.'""")
new_texts = spark.sql(f"""
  SELECT DISTINCT sha2(sentence_text, 256) AS text_hash, sentence_text
  FROM {ns}.silver_sentences
  WHERE speaker = 'customer' AND size(split(sentence_text, ' ')) >= 4
  EXCEPT SELECT text_hash, sentence_text FROM {ns}.ai_classify_cache""")
new_texts.createOrReplaceTempView("new_texts")
n_new = new_texts.count()
print(f"new distinct sentences to classify: {n_new:,}")
t0 = time.time()
if n_new:
    spark.sql(f"""
      INSERT INTO {ns}.ai_classify_cache
      SELECT text_hash, sentence_text,
             to_json(ai_classify(sentence_text, :labels,
                     map('version', '2.1', 'multilabel', 'true', 'enableConfidenceScores', 'true',
                         'enableRationales', 'true', 'instructions', :instructions))) AS ai_result,
             current_timestamp()
      FROM new_texts""", args={"labels": LABELS, "instructions": INSTRUCTIONS})
elapsed = round(time.time() - t0, 1)

# COMMAND ----------
spark.sql(f"""
CREATE OR REPLACE TABLE {ns}.sentence_ai_tags
COMMENT 'ai_classify topic tags per customer sentence (confidence-gated), joined back from the distinct-text cache.'
AS
WITH parsed AS (
  SELECT text_hash, explode(from_json(ai_result,
           'struct<response:array<struct<value:string,confidence_score:double,rationale:string>>>').response) AS r
  FROM {ns}.ai_classify_cache)
SELECT s.sentence_id, s.interaction_id, t.topic_id, t.topic_name, t.parent_topic,
       p.r.confidence_score AS confidence, p.r.rationale
FROM {ns}.silver_sentences s
JOIN parsed p ON sha2(s.sentence_text, 256) = p.text_hash
JOIN {ns}.dim_topics t ON t.topic_name = p.r.value
WHERE s.speaker = 'customer' AND coalesce(p.r.confidence_score, 1.0) >= {min_conf}""")

summary = spark.sql(f"SELECT topic_name, count(*) n, round(avg(confidence),3) avg_conf FROM {ns}.sentence_ai_tags GROUP BY 1 ORDER BY 2 DESC").toPandas()
cache_n = spark.table(f"{ns}.ai_classify_cache").count()
print(f"ai_classify calls this run: {n_new:,} in {elapsed}s | cache size: {cache_n:,}")
print(summary.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/04_ai_classify.json", "w") as f:
    json.dump({"ai_calls_this_run": n_new, "seconds": elapsed, "cache_size": cache_n, "min_confidence": min_conf,
               "tags_by_topic": summary.to_dict("records"),
               "examples": spark.sql(f"""SELECT a.topic_name, s.sentence_text, a.confidence, a.rationale
                   FROM {ns}.sentence_ai_tags a JOIN {ns}.silver_sentences s USING (sentence_id)
                   ORDER BY rand(7) LIMIT 8""").toPandas().to_dict("records")}, f, indent=2)
