#!/usr/bin/env bash
# Pull run evidence (as TEXT) from the workspace into ./evidence so it can be committed.
# Usage: scripts/collect_evidence.sh <profile> <job_run_id>
set -euo pipefail
P=${1:?profile}; RUN=${2:?job run id}
W=148ccb90800933a1; NS=daria_krasavina.voc_valtera
cd "$(dirname "$0")/.."; mkdir -p evidence/task_outputs evidence/query_results

# 1. per-task evidence JSON written by every notebook
for f in 01_governance 02_rule_tagging 03_ai_classify 04_sentiment_model 05_gold_and_alerts 06_lakebase_sync 07_evaluate 08_genie_space; do
  databricks fs cat "dbfs:/Volumes/daria_krasavina/voc_valtera/evidence/$f.json" --profile "$P" > "evidence/task_outputs/$f.json"
done

# 2. job run summary (task states, durations)
databricks jobs get-run "$RUN" --profile "$P" -o json | python3 -c '
import json,sys; r=json.load(sys.stdin)
print("job run", r["run_id"], r["state"].get("result_state"), "| run page:", r["run_page_url"])
for t in sorted(r["tasks"], key=lambda t: t["start_time"]):
    secs = round((t.get("end_time", 0) - t.get("start_time", 0)) / 1000)
    print("  %-18s %-8s %5ss" % (t["task_key"], t["state"].get("result_state", ""), secs))' > evidence/job_run_summary.txt


# 4. key query results straight from Unity Catalog
q() { databricks experimental aitools tools query "$2" --warehouse $W --profile "$P" > "evidence/query_results/$1.json"; }
q table_row_counts "SELECT 'bronze_interactions' t, count(*) n FROM $NS.bronze_interactions UNION ALL SELECT 'silver_sentences', count(*) FROM $NS.silver_sentences UNION ALL SELECT 'silver_customers', count(*) FROM $NS.silver_customers UNION ALL SELECT 'gold_interaction_insights', count(*) FROM $NS.gold_interaction_insights UNION ALL SELECT 'gold_sentence_topics', count(*) FROM $NS.gold_sentence_topics UNION ALL SELECT 'gold_escalation_queue', count(*) FROM $NS.gold_escalation_queue UNION ALL SELECT 'lb_escalation_queue (Lakebase)', count(*) FROM $NS.lb_escalation_queue"
q emerging_issues "SELECT topic_name, model, model_year, first_alert_date, peak_lift, last_7d, is_alert FROM $NS.gold_emerging_issues WHERE first_alert_date IS NOT NULL ORDER BY first_alert_date"
q classifier_quality "SELECT * FROM $NS.eval_classification_metrics ORDER BY f1 DESC"
q escalation_queue_sample "SELECT case_id, priority, primary_topic, model, model_year, dealer_name, case_summary, recommended_action FROM $NS.gold_escalation_queue ORDER BY escalation_score DESC LIMIT 10"
q metric_view_by_vehicle "SELECT model, model_year, MEASURE(interactions) AS interactions, MEASURE(safety_interactions) AS safety_interactions, MEASURE(negative_rate_pct) AS negative_rate_pct, MEASURE(avg_nps) AS avg_nps FROM $NS.mv_voc_metrics GROUP BY ALL ORDER BY safety_interactions DESC"
q explainable_rule_tags "SELECT r.topic_name, s.sentence_text, r.matched_terms FROM $NS.sentence_rule_tags r JOIN $NS.silver_sentences s USING (sentence_id) WHERE r.via = 'direct' AND r.topic_id IN ('saf_unexpected_braking','chg_charge_port') LIMIT 6"
q ai_only_catches "SELECT topic_name, ai_confidence, ai_rationale, s.sentence_text FROM $NS.gold_sentence_topics t JOIN $NS.silver_sentences s USING (sentence_id) WHERE detected_by = 'ai' GROUP BY ALL LIMIT 10"
q masked_pii "SELECT customer_id, first_name, last_name, email, phone, loyalty_tier FROM $NS.customers_secure LIMIT 5"
q uc_model_versions "SELECT 'voc_sentiment_model' AS model, '$NS.voc_sentiment_model' AS full_name"

# 5. incremental ingestion proof: rows written per Auto Loader update (Delta history)
for t in bronze_interactions silver_sentences; do
  databricks experimental aitools tools query "SELECT '$t' AS table_name, version, CAST(timestamp AS STRING) AS ts, operation, operationMetrics.numOutputRows AS rows_written FROM (DESCRIBE HISTORY $NS.$t) WHERE operation IN ('STREAMING UPDATE', 'CREATE OR REPLACE TABLE', 'WRITE') ORDER BY version" --warehouse $W --profile "$P"
done > evidence/query_results/incremental_delta_history.json
q case_status "SELECT status, priority, count(*) AS cases FROM $NS.gold_case_status GROUP BY ALL ORDER BY priority, status"
q sentiment_mix "SELECT sentiment, count(*) AS interactions, round(100 * count(*) / sum(count(*)) OVER (), 1) AS pct FROM $NS.gold_interaction_insights GROUP BY 1"
q messy_bronze_vs_clean_silver "SELECT b.customer_id, b.first_name AS bronze_first_name, s.first_name AS silver_first_name, b.phone AS bronze_phone, s.phone AS silver_phone, b.loyalty_tier AS bronze_tier, s.loyalty_tier AS silver_tier FROM $NS.bronze_customers b JOIN $NS.silver_customers s USING (customer_id) WHERE b.loyalty_tier <> s.loyalty_tier OR b.first_name <> s.first_name LIMIT 8"
q transcript_sample "SELECT interaction_id, turn_idx, speaker, sentence_text FROM $NS.silver_sentences WHERE interaction_id = (SELECT min(interaction_id) FROM $NS.silver_sentences WHERE channel = 'call' AND interaction_date = '2026-11-05') ORDER BY turn_idx, sentence_idx"

# 6. unit tests
(uv run --no-project --with pytest python -m pytest tests -v 2>&1 || true) > evidence/unit_tests.txt
echo "evidence collected in ./evidence"
# Public repo: redact any personal email
grep -rl '@databricks.com' evidence | while read f; do python3 -c "import re,sys; p=sys.argv[1]; s=open(p).read(); open(p,'w').write(re.sub(r'[A-Za-z0-9._%+-]+@databricks\\.com', '<redacted>', s))" "$f"; done  # redact any personal email
