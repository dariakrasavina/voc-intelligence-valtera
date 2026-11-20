# Databricks notebook source
# MAGIC %md
# MAGIC # 08 · Genie Agent "Valtera VOC Insights": create, curate, benchmark
# MAGIC Creates (or updates, if it already exists) the Genie Agent over the gold tables, then runs its benchmarks.
# MAGIC Curation follows the Databricks Genie guidance (structured context first, text instructions last):
# MAGIC
# MAGIC | Surface | What is defined here |
# MAGIC |---|---|
# MAGIC | Tables + column configs | descriptions, synonyms, entity matching on categorical columns, hidden sensitive columns |
# MAGIC | Join specs | how the gold tables relate (with relationship type) |
# MAGIC | SQL snippets | governed **measures**, **filters** and **expressions** (column-qualified) |
# MAGIC | Example SQL | one example per query shape (trend, ranking, ratio, parameterized drill-down, metric view) |
# MAGIC | Text instructions | short, only what cannot be expressed structurally |
# MAGIC | Benchmarks | business questions with checked ground-truth SQL; the task **fails below 90% correct** |
# MAGIC
# MAGIC Every example, snippet and benchmark SQL is executed on the warehouse before it is pushed.

# COMMAND ----------
import json, os, re, time, uuid
from databricks.sdk import WorkspaceClient
from pyspark.sql import functions as F

for k, v in {"catalog": "daria_krasavina", "schema": "voc_valtera", "warehouse_id": "148ccb90800933a1",
             "min_pass_rate": "0.9", "run_benchmarks": "true",
             "evidence_path": "/Volumes/daria_krasavina/voc_valtera/evidence"}.items():
    dbutils.widgets.text(k, v)
cat, sch, wh, ev = (dbutils.widgets.get(k) for k in ["catalog", "schema", "warehouse_id", "evidence_path"])
MIN_PASS = float(dbutils.widgets.get("min_pass_rate"))
RUN_BENCH = dbutils.widgets.get("run_benchmarks").lower() == "true"
NS = f"{cat}.{sch}"
TITLE = "Valtera VOC Insights"
DESCRIPTION = ("Ask about Valtera Motors customer calls and surveys: complaint topics, sentiment, safety signals, "
               "emerging issues by model and model year, dealers and the escalation queue. Synthetic data.")
w = WorkspaceClient()


def _id(seed):
    """Stable 32-hex id, so re-running the notebook updates items instead of duplicating them."""
    return uuid.uuid5(uuid.NAMESPACE_URL, "valtera-voc-genie/" + seed).hex

# COMMAND ----------
# MAGIC %md ## 1 · Tables and column configs

# COMMAND ----------
def col(name, desc=None, synonyms=None, match=False, exclude=False):
    c = {"column_name": name}
    if desc: c["description"] = [desc]
    if synonyms: c["synonyms"] = synonyms
    if match:
        c["enable_format_assistance"] = True
        c["enable_entity_matching"] = True
    if exclude: c["exclude"] = True
    return c

MODEL = col("model", "Vehicle model: Aurora EV, Strata EV, Ridgeback, Ridgeback Hybrid, Cove.", ["vehicle", "car", "nameplate"], match=True)
MODEL_YEAR = col("model_year", "Vehicle model year (integer, e.g. 2026).", ["MY", "year model"])
POWERTRAIN = col("powertrain", "EV, HYBRID or ICE. Hybrids are not ICE.", ["drivetrain", "electric", "gas"], match=True)
DEALER = col("dealer_name", "Selling / servicing dealer, e.g. 'Lakeshore Valtera'.", ["dealer", "dealership", "store"], match=True)
REGION = col("dealer_region", "Dealer region: Midwest, Northeast, South, West.", ["region"], match=True)
TOPIC = col("topic_name", "Leaf complaint topic, e.g. 'Charging - Charge Port Door Stuck', 'Safety - Unexpected Braking'.", ["topic", "issue", "complaint type"], match=True)
PARENT = col("parent_topic", "Topic group: Battery & Charging, Vehicle Safety, Software & Connectivity, Service & Warranty, "
             "Dealer & Sales Experience, Billing & Financing, Positive Feedback.", ["topic group", "category"], match=True)
CHANNEL = col("channel", "'call' (contact center) or 'survey' (post-service survey).", ["source"], match=True)

TABLES = {
    f"{NS}.gold_interaction_insights": [
        col("interaction_id", "One row per customer interaction (a call or a survey).", ["contact", "case id"]),
        CHANNEL, MODEL, MODEL_YEAR, POWERTRAIN, DEALER, REGION,
        col("interaction_date", "Date of the call or survey.", ["date", "day"]),
        col("primary_topic", "The single most severe topic of the interaction ('No topic detected' if none). "
            "Use only for 'main issue' questions; to count mentions of a topic use topics or gold_topic_daily.", ["main issue"], match=True),
        col("primary_parent_topic", "Topic group of primary_topic.", ["main topic group"], match=True),
        col("topics", "Array of every topic mentioned. Filter with array_contains(topics, '<topic_name>')."),
        col("is_safety", "True if any Vehicle Safety topic was mentioned.", ["safety", "safety complaint"]),
        col("sentiment", "negative / neutral / positive, from the trained sentiment model.", ["tone"], match=True),
        col("priority", "P1 = safety or escalation score >= 6, P2 = score >= 3, P3 = rest.", ["severity"], match=True),
        col("escalation_score", "Severity score: topic weight x negativity, + NPS and safety boosts."),
        col("nps_score", "Net Promoter Score 0-10, surveys only (NULL for calls). Detractor = 0-6, promoter = 9-10.", ["NPS", "score"]),
        col("loyalty_tier", "Standard, Silver or Gold.", ["tier", "membership"], match=True),
        col("call_reason", "Reason code chosen by the agent at the start of the call.", ["reason"], match=True),
        col("vin", exclude=True), col("customer_text", exclude=True),
    ],
    f"{NS}.gold_topic_daily": [
        col("interaction_date", "Day.", ["date"]),
        TOPIC, PARENT, MODEL, MODEL_YEAR, POWERTRAIN, DEALER, REGION, CHANNEL,
        col("interactions", "Interactions that mentioned the topic that day. SUM it across rows; do not add across "
            "topics to get total interactions (one interaction can mention several topics).", ["mentions", "complaints", "volume"]),
        col("negative_interactions", "Of those, interactions with negative sentiment.", ["negative mentions"]),
        col("p1_interactions", "Of those, interactions with priority P1.", ["P1 mentions"]),
    ],
    f"{NS}.gold_emerging_issues": [
        TOPIC, PARENT, MODEL, MODEL_YEAR,
        col("is_alert", "True when the alert rule (>= 10 interactions in 7 days and >= 4x the prior 4-week weekly "
            "average) fired in the last 30 days.", ["active alert", "spiking", "emerging", "trending issue"]),
        col("first_alert_date", "First day the alert rule fired for this topic and vehicle.", ["detected on", "first detected"]),
        col("peak_lift", "Size of the spike: the highest lift (last 7 days / baseline) on any alert day. Use this for 'biggest spike' or 'largest increase'.", ["spike", "spike size", "biggest increase", "peak lift"]),
        col("last_7d", "Interactions in the 7 days up to as_of_date.", ["last week"]),
        col("baseline_weekly_avg", "Average weekly interactions in the 4 weeks before the last 7 days.", ["baseline"]),
        col("lift_vs_baseline", "Current lift on the latest day only (last_7d / baseline). Not the spike size; use peak_lift for spikes.", ["current lift"]),
        col("as_of_date", "Latest date in the data."),
    ],
    f"{NS}.gold_escalation_queue": [
        col("case_id", "Case = interaction id of a P1/P2 interaction from the last 30 days.", ["case", "ticket"]),
        col("priority", "P1 or P2.", ["severity"], match=True),
        col("primary_topic", "Most severe topic of the case.", ["issue", "topic"], match=True),
        col("primary_parent_topic", "Topic group of the case.", ["topic group"], match=True),
        MODEL, MODEL_YEAR, POWERTRAIN, DEALER, REGION, CHANNEL,
        col("case_summary", "AI-generated one-line summary of what the customer said.", ["summary"]),
        col("recommended_action", "Suggested next step for the owning team.", ["next step", "action"]),
        col("escalation_score", "Severity score of the case."),
        col("vin", exclude=True),
    ],
    f"{NS}.gold_sentence_topics": [
        col("sentence_text", "The customer's sentence that was tagged.", ["quote", "verbatim", "what customers said"]),
        TOPIC, PARENT, CHANNEL,
        col("detected_by", "'rules' (keyword rule engine), 'ai' (ai_classify only) or 'both'.", ["detection method", "classifier"], match=True),
        col("matched_terms", "Keywords that triggered the rule tag."),
        col("ai_confidence", "ai_classify confidence 0-1."),
        col("ai_rationale", "ai_classify's reason for the tag."),
    ],
    f"{NS}.dim_topics": [TOPIC, PARENT, col("escalation_weight", "Topic severity weight 0-5 (5 = safety critical).", ["severity weight"])],
    f"{NS}.mv_voc_metrics": [],
}

# COMMAND ----------
# MAGIC %md ## 2 · Joins, measures, filters, expressions

# COMMAND ----------
JOINS = [
    ("gold_topic_daily", "dim_topics", "`gold_topic_daily`.`topic_id` = `dim_topics`.`topic_id`", "MANY_TO_ONE"),
    ("gold_escalation_queue", "gold_interaction_insights", "`gold_escalation_queue`.`case_id` = `gold_interaction_insights`.`interaction_id`", "ONE_TO_ONE"),
    ("gold_sentence_topics", "gold_interaction_insights", "`gold_sentence_topics`.`interaction_id` = `gold_interaction_insights`.`interaction_id`", "MANY_TO_ONE"),
    ("gold_emerging_issues", "dim_topics", "`gold_emerging_issues`.`topic_name` = `dim_topics`.`topic_name`", "MANY_TO_ONE"),
]
MEASURES = [  # (alias, display, sql, synonyms)
    ("interaction_count", "Interactions", "COUNT(DISTINCT gold_interaction_insights.interaction_id)", ["number of interactions", "contacts", "volume"]),
    ("negative_rate_pct", "Negative rate %", "ROUND(100.0 * AVG(CASE WHEN gold_interaction_insights.sentiment = 'negative' THEN 1 ELSE 0 END), 1)", ["negative share", "% negative"]),
    ("avg_nps", "Average NPS", "ROUND(AVG(gold_interaction_insights.nps_score), 2)", ["NPS", "net promoter score"]),
    ("detractor_rate_pct", "Detractor rate %", "ROUND(100.0 * AVG(CASE WHEN gold_interaction_insights.nps_score <= 6 THEN 1.0 ELSE 0.0 END), 1)", ["detractors", "% detractors"]),
    ("topic_mentions", "Topic mentions", "SUM(gold_topic_daily.interactions)", ["mentions", "complaints about"]),
    ("p1_case_count", "P1 cases", "COUNT(CASE WHEN gold_escalation_queue.priority = 'P1' THEN 1 END)", ["P1", "critical cases"]),
]
FILTERS = [  # (display, sql, synonyms)
    ("Safety interactions", "gold_interaction_insights.is_safety = true", ["safety complaints", "safety issues"]),
    ("Complaints only", "gold_topic_daily.parent_topic <> 'Positive Feedback'", ["complaints", "problems", "excluding praise"]),
    ("Active alerts", "gold_emerging_issues.is_alert = true", ["spiking now", "current alerts", "emerging"]),
    ("EV owners", "gold_interaction_insights.powertrain = 'EV'", ["electric vehicles", "EVs"]),
    ("Surveys only", "gold_interaction_insights.channel = 'survey'", ["survey responses"]),
    ("Negative interactions", "gold_interaction_insights.sentiment = 'negative'", ["unhappy customers", "negative"]),
]
EXPRESSIONS = [  # (alias, display, sql, synonyms)
    ("interaction_week", "Week", "DATE_TRUNC('WEEK', gold_interaction_insights.interaction_date)", ["week", "weekly"]),
    ("interaction_month", "Month", "DATE_TRUNC('MONTH', gold_interaction_insights.interaction_date)", ["month", "monthly"]),
    ("vehicle", "Vehicle (model + year)", "CONCAT(gold_interaction_insights.model, ' ', CAST(gold_interaction_insights.model_year AS STRING))", ["vehicle", "model and year"]),
]

# COMMAND ----------
# MAGIC %md ## 3 · Example SQL (one per query shape) and text instructions

# COMMAND ----------
EXAMPLES = [  # (question, sql, parameters[(name, type, description, default)], usage)
    ("Which issues are spiking right now?",
     f"SELECT topic_name, model, model_year, first_alert_date, peak_lift, last_7d FROM {NS}.gold_emerging_issues WHERE is_alert ORDER BY peak_lift DESC",
     [], "Emerging / spiking / trending issues: always gold_emerging_issues with is_alert."),
    ("Weekly mentions of a topic for a vehicle",
     f"SELECT DATE_TRUNC('WEEK', interaction_date) AS week, SUM(interactions) AS mentions FROM {NS}.gold_topic_daily WHERE topic_name = :topic AND model = :model AND model_year = :model_year GROUP BY 1 ORDER BY 1",
     [("topic", "STRING", "Leaf topic name", "Safety - Unexpected Braking"), ("model", "STRING", "Vehicle model", "Aurora EV"),
      ("model_year", "STRING", "Model year", "2026")], "Trends of one topic over time: gold_topic_daily, SUM(interactions)."),
    ("Top complaint topics for a powertrain between two dates",
     f"SELECT topic_name, SUM(interactions) AS mentions FROM {NS}.gold_topic_daily WHERE powertrain = :powertrain AND parent_topic <> 'Positive Feedback' AND interaction_date BETWEEN :start_date AND :end_date GROUP BY topic_name ORDER BY mentions DESC LIMIT 10",
     [("powertrain", "STRING", "EV, HYBRID or ICE", "EV"), ("start_date", "STRING", "First day (YYYY-MM-DD)", "2026-10-21"),
      ("end_date", "STRING", "Last day (YYYY-MM-DD)", "2026-11-20")], "Ranking topics: exclude Positive Feedback."),
    ("Dealers with the highest share of negative interactions",
     f"SELECT dealer_name, COUNT(*) AS interactions, ROUND(100.0 * AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 1) AS negative_pct FROM {NS}.gold_interaction_insights GROUP BY dealer_name HAVING COUNT(*) >= 50 ORDER BY negative_pct DESC LIMIT 10",
     [], "Rates per dealer: require a minimum volume."),
    ("Show what customers said about a topic",
     f"SELECT sentence_text, detected_by, matched_terms, ai_confidence FROM {NS}.gold_sentence_topics WHERE topic_name = :topic ORDER BY ai_confidence DESC NULLS LAST LIMIT 20",
     [("topic", "STRING", "Leaf topic name", "Charging - Charge Port Door Stuck")], "Verbatims / quotes / examples: gold_sentence_topics.sentence_text."),
    ("Open P1 and P2 cases by topic group",
     f"SELECT primary_parent_topic, priority, COUNT(*) AS cases FROM {NS}.gold_escalation_queue GROUP BY ALL ORDER BY priority, cases DESC",
     [], "Escalation queue questions: gold_escalation_queue."),
    ("Safety interactions and negative rate by vehicle (metric view)",
     f"SELECT model, model_year, MEASURE(safety_interactions) AS safety_interactions, MEASURE(negative_rate_pct) AS negative_rate_pct FROM {NS}.mv_voc_metrics GROUP BY ALL ORDER BY safety_interactions DESC",
     [], "Governed KPIs by dimension: mv_voc_metrics with MEASURE()."),
]

INSTRUCTIONS = """## PURPOSE
Answer questions about Valtera Motors customer calls and surveys (synthetic data, 2026-08-22 to 2026-11-20): complaint topics, sentiment, safety signals, emerging issues, dealers and the escalation queue.

## DISAMBIGUATION
- "Interactions", "contacts", "complaints" mean distinct calls or surveys. One interaction can mention several topics: count totals in gold_interaction_insights, mentions per topic in gold_topic_daily.
- "Recent", "this month", "last 30 days" are relative to the latest date in the data (2026-11-20).
- A model named without a year means all model years. Powertrain is EV, HYBRID or ICE; hybrids are not ICE.

## DATA QUALITY NOTES
- nps_score exists only for surveys; calls have NULL.

## CONSTRAINTS
- Never return customer names, emails, phone numbers or VINs.

## Instructions you must follow when providing summaries
- Round percentages to 1 decimal. Mention the date range in the text of the answer; do not add date columns to the query result."""

SAMPLE_QUESTIONS = ["Which issues are spiking right now?",
                    "When was the charge port door problem on the 2026 Aurora EV first detected?",
                    "Top complaint topics for EV owners in the last 30 days",
                    "Show what customers said about unexpected braking"]

# COMMAND ----------
# MAGIC %md ## 4 · Benchmarks (ground truth checked below)

# COMMAND ----------
BENCHMARKS = [
    ("How many P1 cases are in the escalation queue?",
     f"SELECT COUNT(*) AS p1_cases FROM {NS}.gold_escalation_queue WHERE priority = 'P1'"),
    ("Which active emerging issue has the biggest spike versus its baseline?",
     f"SELECT topic_name, model, model_year, peak_lift FROM {NS}.gold_emerging_issues WHERE is_alert ORDER BY peak_lift DESC LIMIT 1"),
    ("When was the charge port door problem on the 2026 Aurora EV first detected?",
     f"SELECT first_alert_date FROM {NS}.gold_emerging_issues WHERE topic_name = 'Charging - Charge Port Door Stuck' AND model = 'Aurora EV' AND model_year = 2026"),
    ("How many emerging issue alerts are active?",
     f"SELECT COUNT(*) AS active_alerts FROM {NS}.gold_emerging_issues WHERE is_alert"),
    ("What is the average NPS by vehicle model, all model years combined?",
     f"SELECT model, AVG(nps_score) AS avg_nps FROM {NS}.gold_interaction_insights WHERE channel = 'survey' AND nps_score IS NOT NULL GROUP BY model"),
    ("How many interactions mentioned a charge port door problem for the 2026 Aurora EV?",
     f"SELECT SUM(interactions) AS interactions FROM {NS}.gold_topic_daily WHERE topic_name = 'Charging - Charge Port Door Stuck' AND model = 'Aurora EV' AND model_year = 2026"),
    ("Which dealer has the most poor dealer experience complaints?",
     f"SELECT dealer_name, SUM(interactions) AS complaints FROM {NS}.gold_topic_daily WHERE topic_name = 'Dealer - Poor Dealer Experience' GROUP BY dealer_name ORDER BY complaints DESC LIMIT 1"),
    ("What percent of interactions are negative for each powertrain?",
     f"SELECT powertrain, ROUND(100.0 * AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 1) AS negative_pct FROM {NS}.gold_interaction_insights GROUP BY powertrain"),
    ("How many safety-related interactions were there in October 2026?",
     f"SELECT COUNT(*) AS safety_interactions FROM {NS}.gold_interaction_insights WHERE is_safety AND interaction_date BETWEEN '2026-10-01' AND '2026-10-31'"),
    ("How many interactions came from calls and how many from surveys?",
     f"SELECT channel, COUNT(*) AS interactions FROM {NS}.gold_interaction_insights GROUP BY channel"),
    ("Which complaint topic has the most mentions overall?",
     f"SELECT topic_name, SUM(interactions) AS mentions FROM {NS}.gold_topic_daily WHERE parent_topic <> 'Positive Feedback' GROUP BY topic_name ORDER BY mentions DESC LIMIT 1"),
    ("How many interactions came from Gold tier customers?",
     f"SELECT COUNT(*) AS interactions FROM {NS}.gold_interaction_insights WHERE loyalty_tier = 'Gold'"),
    ("What share of P1 cases in the escalation queue are vehicle safety cases?",
     f"SELECT ROUND(100.0 * AVG(CASE WHEN primary_parent_topic = 'Vehicle Safety' THEN 1 ELSE 0 END), 1) AS safety_share_pct FROM {NS}.gold_escalation_queue WHERE priority = 'P1'"),
    ("How many tagged sentences were found only by the AI classifier and not by the rules?",
     f"SELECT COUNT(*) AS ai_only FROM {NS}.gold_sentence_topics WHERE detected_by = 'ai'"),
    ("What is the average escalation score of P1 cases in the queue?",
     f"SELECT AVG(escalation_score) AS avg_escalation_score FROM {NS}.gold_escalation_queue WHERE priority = 'P1'"),
    ("Which dealer region has the highest average NPS?",
     f"SELECT dealer_region, AVG(nps_score) AS avg_nps FROM {NS}.gold_interaction_insights WHERE channel = 'survey' AND nps_score IS NOT NULL GROUP BY dealer_region ORDER BY avg_nps DESC LIMIT 1"),
    ("What is the detractor rate for surveys?",
     f"SELECT ROUND(100.0 * AVG(CASE WHEN nps_score <= 6 THEN 1.0 ELSE 0.0 END), 1) AS detractor_rate_pct FROM {NS}.gold_interaction_insights WHERE channel = 'survey'"),
    ("Which 3 dealers have the most P1 cases in the escalation queue?",
     f"SELECT dealer_name, COUNT(*) AS p1_cases FROM {NS}.gold_escalation_queue WHERE priority = 'P1' GROUP BY dealer_name ORDER BY p1_cases DESC LIMIT 3"),
    ("How many unexpected braking mentions were there for the 2026 Aurora EV in November 2026?",
     f"SELECT SUM(interactions) AS mentions FROM {NS}.gold_topic_daily WHERE topic_name = 'Safety - Unexpected Braking' AND model = 'Aurora EV' AND model_year = 2026 AND interaction_date BETWEEN '2026-11-01' AND '2026-11-30'"),
    ("How many interactions were there for the Strata EV, all model years?",
     f"SELECT COUNT(*) AS interactions FROM {NS}.gold_interaction_insights WHERE model = 'Strata EV'"),
]

# COMMAND ----------
# MAGIC %md ## 5 · Check every SQL statement on the warehouse before pushing

# COMMAND ----------
from databricks.sdk.service.sql import StatementParameterListItem

def run_sql(sql, params=None):
    r = w.statement_execution.execute_statement(
        warehouse_id=wh, statement=sql, wait_timeout="50s",
        parameters=[StatementParameterListItem(name=n, value=str(v), type=t) for n, t, v in (params or [])])
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(f"{r.status.state.value}: {r.status.error.message if r.status.error else ''}\n{sql}")
    return r.result.data_array if r.result else []

checks = []
for q, sql, params, _ in EXAMPLES:
    rows = run_sql(sql, [(n, t, d) for n, t, _, d in params]); checks.append(("example", q, len(rows)))
for q, sql in BENCHMARKS:
    rows = run_sql(sql); checks.append(("benchmark", q, len(rows)))
    if not rows or rows[0][0] is None:
        raise RuntimeError(f"Benchmark has no answer on current data: {q}")
import re
def snippet_table(sql):
    return re.search(r"\b(gold_\w+|dim_topics)\.", sql).group(1)
for alias, _, sql, _ in MEASURES + EXPRESSIONS:          # measures / expressions: select them from their table
    t = snippet_table(sql); run_sql(f"SELECT {sql} FROM {NS}.{t} AS {t} LIMIT 1"); checks.append(("snippet", alias, 1))
for name, sql, _ in FILTERS:                              # filters: use them as a WHERE clause
    t = snippet_table(sql); run_sql(f"SELECT COUNT(*) FROM {NS}.{t} AS {t} WHERE {sql}"); checks.append(("filter", name, 1))
for l, r, cond, _ in JOINS:                               # joins: run them
    run_sql(f"SELECT COUNT(*) FROM {NS}.{l} AS {l} JOIN {NS}.{r} AS {r} ON {cond}"); checks.append(("join", f"{l}-{r}", 1))
print(f"checked {len(checks)} statements: all succeeded")

# COMMAND ----------
# MAGIC %md ## 6 · Build the serialized space, create or update the agent

# COMMAND ----------
def serialized_space():
    tables = []
    for ident in sorted(TABLES):
        t = {"identifier": ident}
        if TABLES[ident]:
            t["column_configs"] = sorted(TABLES[ident], key=lambda c: c["column_name"])
        tables.append(t)
    sid = lambda items: sorted(items, key=lambda x: x["id"])
    return {
        "version": 2,
        "config": {"sample_questions": sid([{"id": _id("sq/" + q), "question": [q]} for q in SAMPLE_QUESTIONS])},
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": [{"id": _id("ti"), "content": [INSTRUCTIONS]}],
            "example_question_sqls": sid([dict({"id": _id("ex/" + q), "question": [q], "sql": [s], "usage_guidance": [u]},
                                               **({"parameters": [{"name": n, "type_hint": t, "description": [d], "default_value": {"values": [dv]}}
                                                                  for n, t, d, dv in p]} if p else {}))
                                          for q, s, p, u in EXAMPLES]),
            "join_specs": sid([{"id": _id(f"join/{l}/{r}"),
                                "left": {"identifier": f"{NS}.{l}", "alias": l}, "right": {"identifier": f"{NS}.{r}", "alias": r},
                                "sql": [cond, f"--rt=FROM_RELATIONSHIP_TYPE_{rt}--"]} for l, r, cond, rt in JOINS]),
            "sql_snippets": {
                "measures": sid([{"id": _id("m/" + a), "alias": a, "display_name": d, "sql": [s], "synonyms": syn} for a, d, s, syn in MEASURES]),
                "filters": sid([{"id": _id("f/" + d), "display_name": d, "sql": [s], "synonyms": syn} for d, s, syn in FILTERS]),
                "expressions": sid([{"id": _id("e/" + a), "alias": a, "display_name": d, "sql": [s], "synonyms": syn} for a, d, s, syn in EXPRESSIONS]),
            },
        },
        "benchmarks": {"questions": sid([{"id": _id("bm/" + q), "question": [q], "answer": [{"format": "SQL", "content": [s]}]}
                                         for q, s in BENCHMARKS])},
    }

def find_space_id():
    token = None
    while True:
        r = w.api_client.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": token} if token else {})})
        for s in r.get("spaces", []):
            if s.get("title") == TITLE:
                return s["space_id"]
        token = r.get("next_page_token")
        if not token:
            return None

payload = {"title": TITLE, "description": DESCRIPTION, "warehouse_id": wh, "serialized_space": json.dumps(serialized_space())}
space_id = find_space_id()
if space_id:
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=payload); action = "updated"
else:
    space_id = w.api_client.do("POST", "/api/2.0/genie/spaces", body=payload)["space_id"]; action = "created"
host = w.config.host.rstrip("/")
print(f"{action} Genie Agent '{TITLE}': {host}/genie/rooms/{space_id}")
print(f"  {len(TABLES)} tables, {len(JOINS)} joins, {len(MEASURES)} measures, {len(FILTERS)} filters, "
      f"{len(EXPRESSIONS)} expressions, {len(EXAMPLES)} example SQL, {len(BENCHMARKS)} benchmarks")

# COMMAND ----------
# MAGIC %md ## 7 · Run the benchmarks (fails the task below the pass threshold)

# COMMAND ----------
summary = {"space_id": space_id, "action": action, "benchmarks": len(BENCHMARKS)}
if RUN_BENCH:
    base = f"/api/2.0/genie/spaces/{space_id}/eval-runs"
    run = w.api_client.do("POST", base, body={})
    run_id = run["eval_run_id"]
    for _ in range(90):
        time.sleep(10)
        run = w.api_client.do("GET", f"{base}/{run_id}")
        if run.get("eval_run_status") == "DONE":
            break
    results = []
    for r in w.api_client.do("GET", f"{base}/{run_id}/results").get("eval_results", []):
        d = w.api_client.do("GET", f"{base}/{run_id}/results/{r['result_id']}")
        actual = ((d.get("actual_response") or [{}])[0]).get("response", "")
        results.append({"question": r["question"], "assessment": d.get("assessment"),
                        "reasons": ", ".join(d.get("assessment_reasons") or []), "genie_sql": actual})
    n_good = sum(1 for r in results if r["assessment"] == "GOOD")
    pass_rate = n_good / max(len(results), 1)
    summary.update({"eval_run_id": run_id, "correct": n_good, "questions": len(results), "pass_rate": round(pass_rate, 3),
                    "needs_review": sum(1 for r in results if r["assessment"] == "NEEDS_REVIEW"), "results": results})
    for r in sorted(results, key=lambda r: r["assessment"] or ""):
        print(f"{r['assessment']:<13} {r['question']}" + (f"   [{r['reasons']}]" if r["reasons"] else ""))
    print(f"\nbenchmark pass rate: {n_good}/{len(results)} = {pass_rate:.0%} (threshold {MIN_PASS:.0%})")
    spark.createDataFrame([{k: r[k] for k in ("question", "assessment", "reasons", "genie_sql")} for r in results]) \
         .withColumn("eval_run_id", F.lit(run_id)) \
         .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{NS}.genie_benchmark_results")

os.makedirs(ev, exist_ok=True)
with open(f"{ev}/08_genie_space.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
if RUN_BENCH and summary["pass_rate"] < MIN_PASS:
    raise RuntimeError(f"Genie benchmark pass rate {summary['pass_rate']:.0%} is below {MIN_PASS:.0%}")
