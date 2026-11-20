# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Rule-engine topic tagging (deterministic, explainable)
# MAGIC Runs the pure-Python rule engine (`src/classification`) over every sentence with `mapInPandas`.
# MAGIC The rules are **data** (`category_model.json`): business users can change keywords without code.
# MAGIC Every tag records the words that triggered it, so each count in the app is explainable.

# COMMAND ----------
import json, os, sys, time
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
ns = f"{cat}.{sch}"
CLS = os.path.abspath("../classification")
SRC = {m: open(os.path.join(CLS, m + ".py")).read() for m in ["rule_engine", "tagger"]}
RULES = json.load(open(os.path.join(CLS, "category_model.json")))
print(RULES["model_name"], "v" + RULES["version"], "-", sum(n["is_leaf"] for n in RULES["nodes"]), "leaf topics")

# COMMAND ----------
OUT_SCHEMA = ("sentence_id string, interaction_id string, topic_id string, topic_name string, "
              "parent_topic string, via string, matched_terms string")
OUT_COLS = [c.split()[0] for c in OUT_SCHEMA.split(", ")]

def make_tagger_fn(src, rules, cols):
    """Self-contained worker function: ships the engine SOURCE (plain strings) to executors and
    builds the modules there, so nothing from the notebook runtime is pickled."""
    def tag_partition(batches):
        import sys, types
        import pandas as pd
        for name in ["rule_engine", "tagger"]:
            if name not in sys.modules:
                mod = types.ModuleType(name)
                sys.modules[name] = mod
                exec(compile(src[name], name + ".py", "exec"), mod.__dict__)
        t = sys.modules["tagger"].build_tagger(rules)
        for pdf in batches:
            rows = []
            for r in pdf.itertuples(index=False):
                attrs = {"speaker": r.speaker, "language": r.language, "channel": r.channel,
                         "powertrain": r.powertrain or ""}
                for tid, hit in t.tag(r.sentence_text, attrs).items():
                    parent = hit["path"][-1] if hit["path"] else hit["name"]
                    rows.append((r.sentence_id, r.interaction_id, tid, hit["name"], parent,
                                 hit["via"], ", ".join(map(str, hit["terms"]))[:500]))
            yield pd.DataFrame(rows, columns=cols)
    return tag_partition

tag_partition = make_tagger_fn(SRC, RULES, OUT_COLS)

sentences = spark.sql(f"""
  SELECT s.sentence_id, s.interaction_id, s.sentence_text, s.speaker, s.language, s.channel, i.powertrain
  FROM {ns}.silver_sentences s JOIN {ns}.silver_interactions i USING (interaction_id)""")
t0 = time.time()
tags = sentences.mapInPandas(tag_partition, OUT_SCHEMA)
tags.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{ns}.sentence_rule_tags")
elapsed = round(time.time() - t0, 1)
spark.sql(f"COMMENT ON TABLE {ns}.sentence_rule_tags IS 'Rule-engine topic tags per sentence (direct + roll-up to parent), with the matched terms that explain each tag.'")

# COMMAND ----------
n_sent = sentences.count()
summary = spark.sql(f"""
  SELECT topic_name, count(*) AS tagged_sentences
  FROM {ns}.sentence_rule_tags WHERE via = 'direct' GROUP BY 1 ORDER BY 2 DESC""").toPandas()
print(f"sentences scanned: {n_sent:,}  |  wall time: {elapsed}s")
print(summary.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/03_rule_tagging.json", "w") as f:
    json.dump({"sentences_scanned": n_sent, "seconds": elapsed,
               "direct_tags_by_topic": summary.to_dict("records"),
               "example_explanations": spark.sql(f"""SELECT r.topic_name, s.sentence_text, r.matched_terms
                    FROM {ns}.sentence_rule_tags r JOIN {ns}.silver_sentences s USING (sentence_id)
                    WHERE r.via='direct' LIMIT 8""").toPandas().to_dict("records")}, f, indent=2)
