#!/usr/bin/env bash
# Pull run evidence (as TEXT) from the workspace into ./evidence so it can be committed.
# Usage: scripts/collect_evidence.sh <profile> <job_run_id>
set -euo pipefail
P=${1:?profile}; RUN=${2:?job run id}
W=148ccb90800933a1; NS=daria_krasavina.voc_valtera
cd "$(dirname "$0")/.."; mkdir -p evidence/task_outputs evidence/query_results

# 1. per-task evidence JSON written by every notebook
for f in 00_land_export 05_governance 10_rule_tagging 20_ai_classify 30_sentiment_model 40_gold_and_alerts 50_lakebase_sync 60_evaluate; do
  databricks fs cat "dbfs:/Volumes/daria_krasavina/voc_valtera/evidence/$f.json" --profile "$P" > "evidence/task_outputs/$f.json"
done

# 2. job run summary (task states, durations)
databricks jobs get-run "$RUN" --profile "$P" -o json | python3 -c '
import json,sys; r=json.load(sys.stdin)
print("job run", r["run_id"], r["state"].get("result_state"), "| run page:", r["run_page_url"])
for t in sorted(r["tasks"], key=lambda t: t["start_time"]):
    secs = round((t.get("end_time", 0) - t.get("start_time", 0)) / 1000)
    print("  %-18s %-8s %5ss" % (t["task_key"], t["state"].get("result_state", ""), secs))' > evidence/job_run_summary.txt

# 3. Lakeflow pipeline: latest update events (row counts, expectations)
PID=$(databricks pipelines list-pipelines --filter "name LIKE 'valtera-voc-ingest'" --profile "$P" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["pipeline_id"])')
databricks pipelines list-pipeline-events "$PID" --max-results 200 --profile "$P" -o json | python3 -c '
import json,sys
ev=json.load(sys.stdin)
for e in ev:
    d=e.get("details",{}); fp=d.get("flow_progress",{})
    if fp.get("metrics") or fp.get("data_quality") or e["event_type"] in ("update_progress",):
        print(e["timestamp"], e["event_type"], e.get("origin",{}).get("flow_name",""), json.dumps({k:fp[k] for k in ("status","metrics","data_quality") if k in fp}) or e.get("message",""))' > evidence/pipeline_events.txt

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

# 5. unit tests
(uv run --no-project --with pytest python -m pytest tests -v 2>&1 || true) > evidence/unit_tests.txt
echo "evidence collected in ./evidence"
