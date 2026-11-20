# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Trained sentiment model (MLflow + Unity Catalog)
# MAGIC Calling an LLM for sentiment on every sentence, every day, is a recurring token bill. Instead:
# MAGIC 1. **Weak-label** a sample of distinct customer sentences once with `ai_analyze_sentiment`.
# MAGIC 2. **Train** a small TF-IDF + logistic-regression model on those labels.
# MAGIC 3. **Track + register** it in MLflow / Unity Catalog (`@champion` alias) and score every sentence at ~zero cost.
# MAGIC
# MAGIC Trade-off (documented): weak labels are not human ground truth. The next step with a real
# MAGIC customer is to have analysts adjudicate a few hundred sentences and retrain.

# COMMAND ----------
# MAGIC %pip install scikit-learn==1.5.2
# MAGIC %restart_python

# COMMAND ----------
import json, os
import mlflow, numpy as np, pandas as pd
from mlflow.models import infer_signature
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera", "label_sample": "2500",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
n_label = int(dbutils.widgets.get("label_sample"))
ns = f"{cat}.{sch}"
MODEL_NAME = f"{ns}.voc_sentiment_model"
print(f"Training {MODEL_NAME} on up to {n_label} weak-labelled customer sentences")

# COMMAND ----------
# 1. Weak labels (cached: only new sentences are sent to the LLM)
spark.sql(f"""CREATE TABLE IF NOT EXISTS {ns}.sentiment_weak_labels
  (sentence_text STRING, weak_label STRING, labeled_at TIMESTAMP)
  COMMENT 'ai_analyze_sentiment weak labels used to train voc_sentiment_model (not human ground truth).'""")
spark.sql(f"""
  INSERT INTO {ns}.sentiment_weak_labels
  SELECT sentence_text, ai_analyze_sentiment(sentence_text), current_timestamp()
  FROM (SELECT DISTINCT sentence_text FROM {ns}.silver_sentences
        WHERE speaker = 'customer' AND size(split(sentence_text, ' ')) >= 3
        EXCEPT SELECT sentence_text FROM {ns}.sentiment_weak_labels
        ORDER BY rand(11) LIMIT {n_label})""")
lab = spark.sql(f"""SELECT sentence_text,
                   CASE WHEN weak_label = 'mixed' THEN 'negative' ELSE weak_label END AS label
                   FROM {ns}.sentiment_weak_labels WHERE weak_label IS NOT NULL""").toPandas()
print(lab.label.value_counts().to_string())

# COMMAND ----------
# 2. Train + 3. log/register
X_tr, X_te, y_tr, y_te = train_test_split(lab.sentence_text, lab.label, test_size=0.2,
                                          random_state=7, stratify=lab.label)
pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
                 ("clf", LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced"))])
me = spark.sql("SELECT current_user()").first()[0]
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(f"/Users/{me}/valtera-voc-sentiment")
with mlflow.start_run(run_name="tfidf_logreg_weak_labels") as run:
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    metrics = {"accuracy": accuracy_score(y_te, pred), "macro_f1": f1_score(y_te, pred, average="macro"),
               "n_train": len(X_tr), "n_test": len(X_te)}
    mlflow.log_params({"vectorizer": "tfidf_1_2gram", "model": "logreg_C4_balanced", "label_source": "ai_analyze_sentiment"})
    mlflow.log_metrics(metrics)
    report = classification_report(y_te, pred)
    mlflow.log_text(report, "classification_report.txt")
    info = mlflow.sklearn.log_model(pipe, name="model", registered_model_name=MODEL_NAME,
                                    signature=infer_signature(X_tr.to_frame(), pred),
                                    input_example=X_tr.head(3).to_frame())
print(json.dumps(metrics, indent=2)); print(report)
from mlflow import MlflowClient
client = MlflowClient()
version = info.registered_model_version
client.set_registered_model_alias(MODEL_NAME, "champion", version)
print(f"registered {MODEL_NAME} v{version} @champion")

# COMMAND ----------
# Score every customer sentence with the @champion model (distinct texts, joined back)
champion = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
texts = spark.sql(f"SELECT DISTINCT sentence_text FROM {ns}.silver_sentences WHERE speaker='customer'").toPandas()
proba = champion.predict_proba(texts.sentence_text)
classes = list(champion.classes_)
texts["sentiment_label"] = np.array(classes)[proba.argmax(1)]
texts["negative_prob"] = proba[:, classes.index("negative")]
texts["sentiment_score"] = proba[:, classes.index("positive")] - texts["negative_prob"]
spark.createDataFrame(texts).createOrReplaceTempView("scored_texts")
spark.sql(f"""CREATE OR REPLACE TABLE {ns}.sentence_sentiment
  COMMENT 'Sentence sentiment from voc_sentiment_model@champion (score = P(positive) - P(negative)).' AS
  SELECT s.sentence_id, s.interaction_id, t.sentiment_label, t.negative_prob, t.sentiment_score,
         '{MODEL_NAME}' AS model_name, {version} AS model_version
  FROM {ns}.silver_sentences s JOIN scored_texts t USING (sentence_text)
  WHERE s.speaker = 'customer'""")
dist = spark.sql(f"SELECT sentiment_label, count(*) n FROM {ns}.sentence_sentiment GROUP BY 1").toPandas()
print(dist.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/04_sentiment_model.json", "w") as f:
    json.dump({"model": MODEL_NAME, "version": int(version), "alias": "champion", "mlflow_run_id": run.info.run_id,
               "metrics_vs_weak_labels": metrics, "classification_report": report,
               "weak_label_distribution": lab.label.value_counts().to_dict(),
               "scored_distribution": dist.to_dict("records")}, f, indent=2)
