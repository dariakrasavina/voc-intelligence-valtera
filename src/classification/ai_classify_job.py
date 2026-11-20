"""
ai_classify_job.py
------------------
GenAI topic classification with the Databricks built-in `ai_classify()` SQL function,
version 2.1. Ported from the ai_classify track of an earlier VOC project of mine.

  ai_classify(text, labels, MAP('version','2.1', 'multilabel','true',
                                'enableConfidenceScores','true', 'enableRationales','true',
                                'instructions', ...))

* LABELS come from the SAME category_model.json the rule engine uses: each target
  category's `ai_description` (ai_common.labels_json). Editing a definition in that file
  changes what ai_classify is asked, with no code change.
* MULTI-LABEL + CONFIDENCE: every applicable label comes back with a 0-1 score. Labels
  below `min_confidence` are dropped (over-tagging gate). The full, ungated response is
  stored in ai_result_json, so the threshold can be re-tuned without re-running inference.
* COST: one call per DISTINCT customer sentence (>= 4 words), cached in
  <ns>.ai_classify_cache keyed by (sentence text hash, definitions fingerprint).
  The fingerprint hashes the labels + definitions + instructions + version, so if
  anyone edits a topic definition, every sentence is re-classified automatically;
  unchanged definitions reuse the cache and cost nothing.

OUTPUT  <ns>.sentence_ai_tags   one row per (sentence, topic): the SENTENCE TEXT, topic,
                                confidence, rationale (confidence-gated)
        <ns>.ai_classify_cache  one row per (distinct sentence, definitions fingerprint)
        <ns>.dim_topics         topic id / name / parent / escalation weight (from the model)
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from ai_common import definitions_fingerprint, find_category_model, labels_json  # noqa: E402

VERSION = "2.1"
INSTRUCTIONS = (
    "You label one sentence a customer said to an automaker's contact center or wrote in a "
    "post-service survey. Classify ONLY the customer's own words. Assign a category ONLY when the "
    "sentence CLEARLY and EXPLICITLY expresses it. MOST sentences match nothing: return no labels for "
    "greetings, small talk, acknowledgments, vehicle descriptions without a problem, and generic or "
    "short clarifying questions. Each category's definition states exactly when to assign it - "
    "follow those definitions precisely.")

# v2.1 return struct (missing optional fields become null via from_json).
RESULT_SCHEMA = ("struct<response:array<struct<value:string,confidence_score:double,"
                 "rationale:string>>,error_message:string>")


def run(spark, ns, rules_path=None, min_confidence=0.6, min_words=4):
    model_path = find_category_model(rules_path)
    model = json.load(open(model_path))
    labels = labels_json(model_path)
    fp = definitions_fingerprint(labels, INSTRUCTIONS, VERSION)
    print("labels: %d target categories from %s | definitions fingerprint %s"
          % (len(json.loads(labels)), os.path.basename(model_path), fp))

    # Topic dimension, straight from the model file.
    leaves = [n for n in model["nodes"] if n.get("is_leaf")]
    spark.createDataFrame([(n["id"], n["name"], n["path"][-1], int(n.get("escalation_weight", 1))) for n in leaves],
                          "topic_id string, topic_name string, parent_topic string, escalation_weight int") \
         .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(ns + ".dim_topics")

    spark.sql("""CREATE TABLE IF NOT EXISTS %s.ai_classify_cache (
        text_hash STRING, definitions_fp STRING, sentence_text STRING,
        ai_result_json STRING, classified_at TIMESTAMP)
        COMMENT 'One ai_classify call per (distinct customer sentence, definitions fingerprint).'""" % ns)
    # Older cache rows (before the fingerprint was part of the key) are not reusable.
    cols = [r.col_name for r in spark.sql("DESCRIBE TABLE %s.ai_classify_cache" % ns).collect()]
    if "definitions_fp" not in cols:
        spark.sql("DROP TABLE %s.ai_classify_cache" % ns)
        return run(spark, ns, rules_path, min_confidence, min_words)

    spark.sql("""
        SELECT DISTINCT sha2(sentence_text, 256) AS text_hash, sentence_text
        FROM {ns}.silver_sentences
        WHERE speaker = 'customer' AND lower(language) = 'english'
          AND size(array_remove(split(trim(sentence_text), ' '), '')) >= {mw}
        EXCEPT
        SELECT text_hash, sentence_text FROM {ns}.ai_classify_cache WHERE definitions_fp = '{fp}'
    """.format(ns=ns, mw=int(min_words), fp=fp)).createOrReplaceTempView("ai_new_texts")
    n_new = spark.table("ai_new_texts").count()
    print("distinct sentences needing ai_classify with these definitions: %d" % n_new)

    t0 = time.time()
    if n_new:
        spark.sql("""
            INSERT INTO {ns}.ai_classify_cache
            SELECT text_hash, '{fp}', sentence_text,
                   to_json(ai_classify(sentence_text, :labels,
                           map('version', '{v}', 'multilabel', 'true', 'enableConfidenceScores', 'true',
                               'enableRationales', 'true', 'instructions', :instructions))),
                   current_timestamp()
            FROM ai_new_texts""".format(ns=ns, fp=fp, v=VERSION),
                  args={"labels": labels, "instructions": INSTRUCTIONS})
    elapsed = round(time.time() - t0, 1)

    # Join results back to every sentence; keep labels at/above the confidence gate.
    spark.sql("""
        CREATE OR REPLACE TABLE {ns}.sentence_ai_tags
        COMMENT 'ai_classify v2.1 tags: one row per (sentence, topic) with the sentence text, confidence and rationale (confidence >= {mc}).'
        AS
        WITH r AS (
          SELECT text_hash, explode(from_json(ai_result_json, '{schema}').response) AS x
          FROM {ns}.ai_classify_cache WHERE definitions_fp = '{fp}')
        SELECT s.sentence_id, s.interaction_id, s.created_at, s.channel, s.speaker, s.sentence_text,
               t.topic_id, t.topic_name, t.parent_topic,
               round(r.x.confidence_score, 3) AS confidence, r.x.rationale AS rationale,
               '{fp}' AS definitions_fp
        FROM {ns}.silver_sentences s
        JOIN r ON sha2(s.sentence_text, 256) = r.text_hash
        JOIN {ns}.dim_topics t ON t.topic_name = r.x.value
        WHERE s.speaker = 'customer' AND coalesce(r.x.confidence_score, 0) >= {mc}
    """.format(ns=ns, fp=fp, mc=float(min_confidence), schema=RESULT_SCHEMA))

    cache_n = spark.sql("SELECT count(*) c FROM %s.ai_classify_cache WHERE definitions_fp = '%s'" % (ns, fp)).first().c
    errors = spark.sql("""SELECT count(*) c FROM %s.ai_classify_cache WHERE definitions_fp = '%s'
                          AND from_json(ai_result_json, '%s').error_message IS NOT NULL"""
                       % (ns, fp, RESULT_SCHEMA)).first().c
    print("ai_classify calls this run: %d in %.1fs | cached results for these definitions: %d | errors: %d"
          % (n_new, elapsed, cache_n, errors))
    return {"ai_calls_this_run": n_new, "seconds": elapsed, "cache_size": cache_n, "errors": errors,
            "definitions_fingerprint": fp, "min_confidence": float(min_confidence), "labels": json.loads(labels)}
