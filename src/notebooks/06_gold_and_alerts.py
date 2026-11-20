# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · Gold layer, escalation queue and emerging-issue alerts
# MAGIC * `gold_sentence_topics` – **consensus** of rule engine + ai_classify (rules for precision, AI for recall).
# MAGIC * `gold_interaction_insights` – one row per call/survey: topics, sentiment, escalation score, priority.
# MAGIC * `gold_topic_daily` – daily mentions by topic × model × model year × dealer (feeds Genie + app).
# MAGIC * `gold_emerging_issues` – last 7 days vs. prior 4-week baseline per topic × model × year.
# MAGIC * `gold_escalation_queue` – P1/P2 cases with an AI case summary, synced to **Lakebase** for the app.
# MAGIC * `mv_voc_metrics` – governed metric view (one definition of "negative rate", "safety mentions", ...).

# COMMAND ----------
import json, os
for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "evidence_path"])
ns = f"{cat}.{sch}"
def sql(q): return spark.sql(q.replace("{ns}", ns))

# COMMAND ----------
sql("""
CREATE OR REPLACE TABLE {ns}.gold_sentence_topics
COMMENT 'Topic per sentence. detected_by = rules | ai | both. Rules give explainable precision, ai_classify adds paraphrases the rules miss.'
AS
WITH r AS (SELECT sentence_id, interaction_id, topic_id, matched_terms FROM {ns}.sentence_rule_tags WHERE via = 'direct'),
     a AS (SELECT sentence_id, interaction_id, topic_id, confidence, rationale FROM {ns}.sentence_ai_tags)
SELECT coalesce(r.sentence_id, a.sentence_id) AS sentence_id,
       coalesce(r.interaction_id, a.interaction_id) AS interaction_id,
       t.topic_id, t.topic_name, t.parent_topic, t.escalation_weight,
       CASE WHEN r.topic_id IS NOT NULL AND a.topic_id IS NOT NULL THEN 'both'
            WHEN r.topic_id IS NOT NULL THEN 'rules' ELSE 'ai' END AS detected_by,
       r.matched_terms, a.confidence AS ai_confidence, a.rationale AS ai_rationale
FROM r FULL OUTER JOIN a ON r.sentence_id = a.sentence_id AND r.topic_id = a.topic_id
JOIN {ns}.dim_topics t ON t.topic_id = coalesce(r.topic_id, a.topic_id)
""")

sql("""
CREATE OR REPLACE TEMP VIEW _interaction_base AS
WITH tp AS (
  SELECT interaction_id,
         array_sort(collect_set(topic_name)) AS topics,
         array_sort(collect_set(parent_topic)) AS parent_topics,
         max(escalation_weight) AS max_weight,
         max_by(topic_name, escalation_weight) AS primary_topic,
         max_by(parent_topic, escalation_weight) AS primary_parent_topic,
         max(CASE WHEN parent_topic = 'Vehicle Safety' THEN 1 ELSE 0 END) = 1 AS is_safety
  FROM {ns}.gold_sentence_topics GROUP BY interaction_id),
se AS (
  SELECT interaction_id, avg(sentiment_score) AS avg_sentiment, max(negative_prob) AS max_negative_prob
  FROM {ns}.sentence_sentiment GROUP BY interaction_id)
SELECT i.interaction_id, i.channel, i.created_at, i.interaction_date, i.call_reason, i.nps_score, i.duration_sec,
       i.customer_id, i.vin, i.model, i.powertrain, i.model_year, i.dealer_id, i.dealer_name, i.dealer_region,
       i.loyalty_tier, coalesce(tp.topics, array()) AS topics, coalesce(tp.parent_topics, array()) AS parent_topics,
       coalesce(tp.primary_topic, 'No topic detected') AS primary_topic,
       coalesce(tp.primary_parent_topic, 'No topic detected') AS primary_parent_topic,
       coalesce(tp.is_safety, false) AS is_safety,
       round(se.avg_sentiment, 3) AS avg_sentiment, round(se.max_negative_prob, 3) AS max_negative_prob,
       CASE WHEN se.max_negative_prob >= 0.5 THEN 'negative' WHEN se.avg_sentiment > 0.2 THEN 'positive' ELSE 'neutral' END AS sentiment,
       round(coalesce(tp.max_weight, 0) * (0.5 + coalesce(se.max_negative_prob, 0))
             + CASE WHEN i.nps_score <= 3 THEN 1 ELSE 0 END
             + CASE WHEN tp.is_safety THEN 2 ELSE 0 END, 2) AS escalation_score,
       i.customer_text
FROM {ns}.silver_interactions i LEFT JOIN tp USING (interaction_id) LEFT JOIN se USING (interaction_id)
""")
sql("""
CREATE OR REPLACE TABLE {ns}.gold_interaction_insights AS
SELECT *, CASE WHEN escalation_score >= 6 OR (is_safety AND max_negative_prob >= 0.5) THEN 'P1'
               WHEN escalation_score >= 3 THEN 'P2' ELSE 'P3' END AS priority
FROM _interaction_base""")
sql("""COMMENT ON TABLE {ns}.gold_interaction_insights IS 'One row per customer interaction (call or survey) with topics, model-scored sentiment, escalation score and priority (P1 = safety or score>=6, P2 = score>=3). No PII.'""")

# COMMAND ----------
sql("""
CREATE OR REPLACE TABLE {ns}.gold_topic_daily
COMMENT 'Daily interactions per topic by vehicle model, model year, powertrain, dealer and channel. Grain: date x topic x model x model_year x dealer x channel.'
AS
SELECT g.interaction_date, t.topic_id, t.topic_name, t.parent_topic,
       g.model, g.model_year, g.powertrain, g.dealer_name, g.dealer_region, g.channel,
       count(DISTINCT g.interaction_id) AS interactions,
       count(DISTINCT CASE WHEN g.sentiment = 'negative' THEN g.interaction_id END) AS negative_interactions,
       count(DISTINCT CASE WHEN g.priority = 'P1' THEN g.interaction_id END) AS p1_interactions
FROM {ns}.gold_interaction_insights g
JOIN (SELECT DISTINCT interaction_id, topic_id, topic_name, parent_topic FROM {ns}.gold_sentence_topics) t USING (interaction_id)
GROUP BY ALL""")

sql("""
CREATE OR REPLACE TABLE {ns}.gold_emerging_issues
COMMENT 'Emerging-issue detection per topic x model x model_year, evaluated EVERY day: trailing 7-day interactions vs. the weekly average of the 28 days before that. A day alerts when last_7d >= 10 and lift >= 4. first_alert_date = first day the rule fired; is_alert = the rule fired in the last 30 days.'
AS
WITH daily AS (
  SELECT topic_name, parent_topic, model, model_year, interaction_date,
         datediff(interaction_date, DATE'2026-01-01') AS dn, SUM(interactions) AS n
  FROM {ns}.gold_topic_daily GROUP BY ALL),
rolled AS (
  SELECT *,
    SUM(n) OVER (PARTITION BY topic_name, model, model_year ORDER BY dn RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS last_7d,
    SUM(n) OVER (PARTITION BY topic_name, model, model_year ORDER BY dn RANGE BETWEEN 34 PRECEDING AND 7 PRECEDING) / 4.0 AS baseline_weekly_avg,
    MIN(dn) OVER (PARTITION BY topic_name, model, model_year) AS first_dn
  FROM daily),
scored AS (
  SELECT *, round(last_7d / greatest(coalesce(baseline_weekly_avg, 0), 1.0), 2) AS lift,
         dn - first_dn >= 28 AND last_7d >= 10 AND last_7d / greatest(coalesce(baseline_weekly_avg, 0), 1.0) >= 4 AS alert_day
  FROM rolled),
bounds AS (SELECT max(interaction_date) AS d FROM daily)
SELECT s.topic_name, s.parent_topic, s.model, s.model_year,
       max(b.d) AS as_of_date,
       sum(CASE WHEN s.interaction_date > date_sub(b.d, 7) THEN s.n ELSE 0 END) AS last_7d,
       round(max_by(s.baseline_weekly_avg, s.interaction_date), 2) AS baseline_weekly_avg,
       min(CASE WHEN s.alert_day THEN s.interaction_date END) AS first_alert_date,
       max(CASE WHEN s.alert_day THEN s.lift END) AS peak_lift,
       round(max_by(s.lift, s.interaction_date), 2) AS lift_vs_baseline,
       coalesce(max(CASE WHEN s.alert_day AND s.interaction_date > date_sub(b.d, 30) THEN 1 END), 0) = 1 AS is_alert
FROM scored s CROSS JOIN bounds b
GROUP BY s.topic_name, s.parent_topic, s.model, s.model_year""")

# COMMAND ----------
# Escalation queue -> Lakebase. AI case summaries are cached so only new cases cost tokens.
sql("""CREATE TABLE IF NOT EXISTS {ns}.case_summaries (case_id STRING, case_summary STRING, summarized_at TIMESTAMP)""")
sql("""
INSERT INTO {ns}.case_summaries
SELECT interaction_id, ai_summarize(customer_text, 30), current_timestamp()
FROM {ns}.gold_interaction_insights
WHERE priority IN ('P1', 'P2') AND interaction_id NOT IN (SELECT case_id FROM {ns}.case_summaries)""")
sql("""
CREATE OR REPLACE TEMP VIEW _queue_now AS
SELECT g.interaction_id AS case_id, g.created_at, g.priority, g.escalation_score, g.primary_topic, g.primary_parent_topic,
       array_join(g.topics, '; ') AS topics, g.sentiment, g.nps_score, g.channel, g.model, g.model_year, g.powertrain,
       g.vin, g.dealer_name, g.dealer_region, g.customer_id, g.loyalty_tier,
       coalesce(c.case_summary, left(g.customer_text, 300)) AS case_summary,
       CASE g.primary_parent_topic
         WHEN 'Vehicle Safety' THEN 'Open safety investigation; call customer within 24h; check for related recall/OTA'
         WHEN 'Battery & Charging' THEN 'Route to EV specialist; pull vehicle charging logs'
         WHEN 'Software & Connectivity' THEN 'Route to connected-vehicle support; check OTA version'
         WHEN 'Service & Warranty' THEN 'Route to warranty desk; confirm parts ETA and loaner'
         WHEN 'Dealer & Sales Experience' THEN 'Notify dealer district manager'
         WHEN 'Billing & Financing' THEN 'Route to Valtera Financial billing team'
         ELSE 'Review' END AS recommended_action
FROM {ns}.gold_interaction_insights g LEFT JOIN {ns}.case_summaries c ON c.case_id = g.interaction_id
WHERE g.priority IN ('P1', 'P2')
  AND g.interaction_date > date_sub((SELECT max(interaction_date) FROM {ns}.gold_interaction_insights), 30)""")

# The queue is MERGED, never replaced: the Lakebase synced table streams this table's Change Data Feed,
# and replacing the table would break that stream. MERGE sends Lakebase only the cases that changed.
if not spark.catalog.tableExists(f"{ns}.gold_escalation_queue"):
    sql("""CREATE TABLE {ns}.gold_escalation_queue
           TBLPROPERTIES (delta.enableChangeDataFeed = true)
           AS SELECT * FROM _queue_now""")
else:
    sql("""
    MERGE INTO {ns}.gold_escalation_queue t
    USING _queue_now s ON t.case_id = s.case_id
    WHEN MATCHED AND (t.priority <> s.priority OR t.escalation_score <> s.escalation_score OR t.case_summary <> s.case_summary
                      OR t.topics <> s.topics OR t.sentiment <> s.sentiment) THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
    WHEN NOT MATCHED BY SOURCE THEN DELETE""")
sql("""COMMENT ON TABLE {ns}.gold_escalation_queue IS 'Open P1/P2 cases from the last 30 days, with AI case summary and recommended next action. Maintained with MERGE (CDF on) and synced to Lakebase (triggered) for the case-management app.'""")
merge_stats = (sql("DESCRIBE HISTORY {ns}.gold_escalation_queue")
               .where("operation IN ('MERGE', 'CREATE TABLE AS SELECT')")
               .select("version", "operation", "operationMetrics").first().asDict())
print("escalation queue write:", merge_stats)

# COMMAND ----------
spark.sql("""
CREATE OR REPLACE VIEW {ns}.mv_voc_metrics
WITH METRICS LANGUAGE YAML
COMMENT 'Governed VOC metrics over customer interactions (one row per call/survey).'
AS $$
version: 0.1
source: {ns}.gold_interaction_insights
dimensions:
  - name: interaction_date
    expr: interaction_date
  - name: interaction_week
    expr: DATE_TRUNC('WEEK', interaction_date)
  - name: channel
    expr: channel
  - name: model
    expr: model
  - name: model_year
    expr: model_year
  - name: powertrain
    expr: powertrain
  - name: dealer_name
    expr: dealer_name
  - name: dealer_region
    expr: dealer_region
  - name: primary_topic
    expr: primary_topic
  - name: primary_parent_topic
    expr: primary_parent_topic
  - name: priority
    expr: priority
  - name: loyalty_tier
    expr: loyalty_tier
measures:
  - name: interactions
    expr: COUNT(1)
  - name: negative_rate_pct
    expr: ROUND(100.0 * SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) / COUNT(1), 1)
  - name: safety_interactions
    expr: SUM(CASE WHEN is_safety THEN 1 ELSE 0 END)
  - name: p1_cases
    expr: SUM(CASE WHEN priority = 'P1' THEN 1 ELSE 0 END)
  - name: avg_nps
    expr: ROUND(AVG(nps_score), 2)
  - name: detractor_rate_pct
    expr: ROUND(100.0 * SUM(CASE WHEN nps_score <= 6 THEN 1 ELSE 0 END) / NULLIF(COUNT(nps_score), 0), 1)
  - name: avg_sentiment
    expr: ROUND(AVG(avg_sentiment), 3)
$$""".replace("{ns}", ns))

# COMMAND ----------
alerts = sql("SELECT * FROM {ns}.gold_emerging_issues WHERE is_alert ORDER BY first_alert_date").toPandas()
queue = sql("SELECT priority, primary_parent_topic, count(*) n FROM {ns}.gold_escalation_queue GROUP BY ALL ORDER BY 1, 3 DESC").toPandas()
detect = sql("SELECT detected_by, count(*) n FROM {ns}.gold_sentence_topics GROUP BY 1").toPandas()
print("EMERGING ISSUES (alerts):"); print(alerts.to_string(index=False))
print("\nESCALATION QUEUE:"); print(queue.to_string(index=False))
print("\nTOPIC DETECTION SOURCE:"); print(detect.to_string(index=False))
os.makedirs(ev, exist_ok=True)
with open(f"{ev}/06_gold_and_alerts.json", "w") as f:
    json.dump({"escalation_queue_write": {k: (dict(v) if isinstance(v, dict) else v) for k, v in merge_stats.items()},
               "emerging_issue_alerts": alerts.to_dict("records"), "escalation_queue_by_priority_topic": queue.to_dict("records"),
               "topic_detection_source": detect.to_dict("records"),
               "metric_view_sample": sql("""SELECT model, model_year, MEASURE(interactions) AS interactions,
                    MEASURE(safety_interactions) AS safety, MEASURE(negative_rate_pct) AS neg_pct
                    FROM {ns}.mv_voc_metrics GROUP BY ALL ORDER BY safety DESC LIMIT 10""").toPandas().to_dict("records")},
              f, indent=2, default=str)
