"""
rule_tag_job.py
---------------
PySpark job: deterministic, explainable topic tagging of every sentence with the
rule engine. Ported from the rule-engine job of an earlier VOC project of mine.

It imports the dependency-free tagging core (`tagger.py` + `rule_engine.py`) and
applies it through a vectorized PySpark `pandas_udf`, so the matching logic on the
cluster is byte-identical to what the unit tests check locally (tests/test_rules.py).

INPUT   <ns>.silver_sentences      (one row per sentence, with speaker / language / channel)
        <ns>.silver_interactions   (vehicle powertrain, used as a rule attribute)
OUTPUT  <ns>.sentence_rule_tags     one row per (sentence, topic): the SENTENCE TEXT, the topic,
                                    whether it matched directly or by roll-up to a parent,
                                    and the words that triggered it (the "why")
        <ns>.rule_tag_frequencies   sentences / interactions tagged per topic

Run from src/notebooks/02_rule_tagging.py (job task) or standalone with spark-submit.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Rule attributes the category model reads (see tagger.ATTR_FIELDS).
SENT_ATTRS = ["channel", "speaker", "language"]
META_ATTRS = ["powertrain"]
TEXT_FIELD = "sentence_text"


def make_tag_udf(rules_path):
    """Vectorized pandas_udf that tags a batch of sentences.

    Returns a JSON string per row: {"in_scope": bool, "topics": {id: {"via": ..., "terms": [...]}}}.
    The compiled rules are built once per Python worker and reused across batches.
    """
    from typing import Iterator, Tuple

    import pandas as pd
    from pyspark.sql.functions import pandas_udf
    from pyspark.sql.types import StringType

    _state = {}

    def _tagger():
        if "t" not in _state:
            from tagger import build_tagger, load_rules
            _state["t"] = build_tagger(load_rules(rules_path))
        return _state["t"]

    attr_cols = SENT_ATTRS + META_ATTRS

    # Serverless / Spark Connect rejects the struct-input (pd.DataFrame) pandas-UDF
    # signature, so text + attributes are passed as SEPARATE Series via the
    # Iterator[Tuple[Series, ...]] form (still Arrow-vectorized).
    # Column order at the call site: [sentence_text, *attr_cols].
    @pandas_udf(StringType())
    def tag_udf(batches: Iterator[Tuple[pd.Series, ...]]) -> Iterator[pd.Series]:
        tg = _tagger()
        for cols in batches:
            text_s, attr_series = cols[0], cols[1:]
            out = []
            for i in range(len(text_s)):
                text = text_s.iloc[i] or ""
                attrs = {attr_cols[j]: (attr_series[j].iloc[i] or "") for j in range(len(attr_cols))}
                in_scope, _ = tg.in_scope(text, attrs)
                topics = tg.tag(text, attrs) if in_scope else {}
                out.append(json.dumps({
                    "in_scope": bool(in_scope),
                    "topics": {tid: {"via": v["via"], "terms": [str(t) for t in v["terms"]]}
                               for tid, v in topics.items()},
                }))
            yield pd.Series(out)

    return tag_udf, attr_cols


def run(spark, ns, rules_path):
    from pyspark.sql import functions as F
    from pyspark.sql.types import (ArrayType, BooleanType, MapType, StringType,
                                   StructField, StructType)

    from tagger import build_tagger, load_rules

    rules = load_rules(rules_path)
    tagger = build_tagger(rules)
    topic_meta = tagger.topic_meta()
    print("%s v%s: %d topics (%d leaf)" % (rules.get("model_name"), rules.get("version"),
                                          len(topic_meta), sum(n["is_leaf"] for n in rules["nodes"])))

    # Cheap structural scope first (customer side, English), so the Python UDF only
    # sees rows the engine could tag. The engine's in_scope() still runs in the UDF.
    sent = (spark.table(ns + ".silver_sentences")
            .filter((F.col("speaker") == "customer") & (F.lower("language") == "english")))
    inter = spark.table(ns + ".silver_interactions").select("interaction_id", "powertrain")
    df = sent.join(inter, "interaction_id", "left")

    tag_udf, attr_cols = make_tag_udf(rules_path)
    payload = [F.col(TEXT_FIELD)] + [F.coalesce(F.col(c), F.lit("")).alias(c) for c in attr_cols]

    t0 = time.time()
    result_schema = StructType([
        StructField("in_scope", BooleanType()),
        StructField("topics", MapType(StringType(), StructType([
            StructField("via", StringType()),
            StructField("terms", ArrayType(StringType()))]))),
    ])
    tagged = (df.withColumn("_tags", F.from_json(tag_udf(*payload), result_schema))
                .filter(F.col("_tags.in_scope")))

    # One row per (sentence, topic). Topic metadata comes from the model file.
    meta_rows = [(tid, m["name"], (m["path"][-1] if m["path"] else m["name"]), bool(m["is_target"]))
                 for tid, m in topic_meta.items()]
    meta_df = spark.createDataFrame(meta_rows, "topic_id string, topic_name string, parent_topic string, is_leaf boolean")
    tags = (tagged.select("sentence_id", "interaction_id", "created_at", "channel", "speaker", TEXT_FIELD,
                          F.explode("_tags.topics").alias("topic_id", "hit"))
                  .join(F.broadcast(meta_df), "topic_id")
                  .select("sentence_id", "interaction_id", "created_at", "channel", "speaker", TEXT_FIELD,
                          "topic_id", "topic_name", "parent_topic", "is_leaf",
                          F.when(F.col("hit.via") == "direct", "direct").otherwise("rollup").alias("via"),
                          F.concat_ws(", ", "hit.terms").alias("matched_terms")))
    (tags.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(ns + ".sentence_rule_tags"))
    spark.sql("COMMENT ON TABLE %s.sentence_rule_tags IS 'Rule-engine tags: one row per (sentence, topic) with the "
              "sentence text, direct vs. roll-up match, and the matched terms that explain the tag.'" % ns)
    elapsed = round(time.time() - t0, 1)

    freq = spark.sql("""
        SELECT topic_id, topic_name, parent_topic, is_leaf,
               count(DISTINCT sentence_id)    AS sentences_tagged,
               count(DISTINCT interaction_id) AS interactions_tagged
        FROM %s.sentence_rule_tags GROUP BY ALL""" % ns)
    freq.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(ns + ".rule_tag_frequencies")
    n_scope = df.count()
    print("customer sentences in scope: %d | tag rows written: %d | %.1fs"
          % (n_scope, spark.table(ns + ".sentence_rule_tags").count(), elapsed))
    return {"sentences_in_scope": n_scope, "seconds": elapsed}
