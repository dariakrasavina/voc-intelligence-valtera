"""
genie_space.py
--------------
"Genie Agent as code": the Valtera VOC Genie Agent (tables, column descriptions,
instructions, example SQL, joins, benchmarks) is defined here, version-controlled,
and created/updated through the Databricks CLI.

  python src/genie/genie_space.py --profile <p> --warehouse <id>            # create
  python src/genie/genie_space.py --profile <p> --warehouse <id> --space-id <id>   # update

Only gold, PII-free tables are exposed. customer_id is the only person key.
"""
import argparse
import json
import subprocess
import uuid

NS = "daria_krasavina.voc_valtera"
TITLE = "Valtera VOC Insights"
DESCRIPTION = ("Ask about customer complaints and feedback for Valtera Motors: topics, sentiment, "
               "safety signals, emerging issues by model / model year, dealers and the escalation queue. "
               "Synthetic data.")


def _id(seed):
    return uuid.uuid5(uuid.NAMESPACE_URL, "valtera-voc/" + seed).hex


def col(name, desc=None, synonyms=None, exclude=False, match=False):
    c = {"column_name": name}
    if desc:
        c["description"] = [desc]
    if synonyms:
        c["synonyms"] = synonyms
    if exclude:
        c["exclude"] = True
    if match:
        c["enable_format_assistance"] = True
        c["enable_entity_matching"] = True
    return c


TABLES = [
    {"identifier": f"{NS}.gold_interaction_insights", "column_configs": [
        col("interaction_id", "One row per customer interaction (a call or a survey).", ["case id", "contact"]),
        col("channel", "'call' or 'survey'.", match=True),
        col("primary_topic", "Most severe topic detected in the interaction ('No topic detected' if none).", ["issue", "complaint type"], match=True),
        col("primary_parent_topic", "Topic group: Battery & Charging, Vehicle Safety, Software & Connectivity, Service & Warranty, Dealer & Sales Experience, Billing & Financing, Positive Feedback.", ["category", "topic group"], match=True),
        col("topics", "Array of all topics detected. Use array_contains(topics, '<topic>') to filter."),
        col("is_safety", "True if any Vehicle Safety topic was detected.", ["safety"]),
        col("sentiment", "negative / neutral / positive (from the trained sentiment model).", match=True),
        col("priority", "P1 = safety or escalation_score >= 6, P2 = score >= 3, P3 = rest.", match=True),
        col("model", "Vehicle model: Aurora EV, Strata EV, Ridgeback, Ridgeback Hybrid, Cove.", ["vehicle", "car"], match=True),
        col("model_year", "Vehicle model year (integer).", ["MY", "year model"]),
        col("dealer_name", synonyms=["dealer", "dealership", "store"], match=True),
        col("nps_score", "0-10, surveys only (NULL for calls). Detractor = 0-6.", ["NPS"]),
        col("customer_text", exclude=True),
        col("vin", exclude=True),
    ]},
    {"identifier": f"{NS}.gold_topic_daily", "column_configs": [
        col("interactions", "Distinct interactions mentioning the topic that day. SUM it across rows."),
        col("topic_name", "Leaf topic, e.g. 'Charging - Charge Port Door Stuck'.", ["topic", "issue"], match=True),
        col("parent_topic", synonyms=["topic group", "category"], match=True),
    ]},
    {"identifier": f"{NS}.gold_emerging_issues", "column_configs": [
        col("last_7d", "Interactions in the last 7 days up to as_of_date."),
        col("baseline_weekly_avg", "Average weekly interactions in the 4 weeks before the last 7 days."),
        col("lift_vs_baseline", "Latest last_7d / baseline (baseline floored at 1)."),
        col("first_alert_date", "First day the alert rule fired (>=10 interactions in 7 days and >=4x the prior 4-week weekly average).", ["detected on", "first detected"]),
        col("peak_lift", "Highest lift on any alert day.", ["spike size"]),
        col("is_alert", "True when the alert rule fired in the last 30 days.", ["alert", "spike", "emerging", "active issue"]),
    ]},
    {"identifier": f"{NS}.gold_escalation_queue", "column_configs": [
        col("case_summary", "AI-generated one-line summary of what the customer said."),
        col("recommended_action", "Suggested next step for the owning team."),
        col("vin", exclude=True),
    ]},
    {"identifier": f"{NS}.mv_voc_metrics"},
    {"identifier": f"{NS}.dim_topics"},
]

INSTRUCTIONS = [
    "Data covers synthetic Valtera Motors customer interactions from 2026-08-22 to 2026-11-19. 'This month' / 'recent' means relative to the latest interaction_date in the data, not today's date.\n",
    "Count complaints as DISTINCT interactions (COUNT(DISTINCT interaction_id)) unless the user asks for sentences or mentions.\n",
    "For trends by topic over time use gold_topic_daily and SUM(interactions). For one-row-per-interaction questions (sentiment, NPS, priority) use gold_interaction_insights.\n",
    "For 'emerging', 'spiking' or 'new' issues use gold_emerging_issues (is_alert = true), ordered by peak_lift desc; first_alert_date says when it was first detected.\n",
    "'Safety complaints' means is_safety = true or parent_topic = 'Vehicle Safety'. powertrain has three values: 'EV', 'HYBRID', 'ICE'. 'EV owners' means powertrain = 'EV'; hybrids are NOT ICE, so compare all three unless the user says otherwise.\n",
    "To count interactions that MENTION a topic, use gold_topic_daily (SUM(interactions)) or array_contains(topics, '<topic>') in gold_interaction_insights. primary_topic is only the single most severe topic of an interaction; use it only when the user asks for the main or primary issue.\n",
    "Never return customer names, emails, phone numbers or VINs; they are not available. customer_id is fine.\n",
    "Round percentages to 1 decimal. When the user names a model without a year, aggregate across all model years.\n",
]

EXAMPLES = [
    ("Which issues are spiking right now?",
     f"SELECT topic_name, model, model_year, first_alert_date, peak_lift, last_7d FROM {NS}.gold_emerging_issues WHERE is_alert ORDER BY peak_lift DESC"),
    ("Top complaint topics for EV owners in the last 30 days",
     f"SELECT topic_name, SUM(interactions) AS interactions FROM {NS}.gold_topic_daily WHERE powertrain = 'EV' AND parent_topic <> 'Positive Feedback' AND interaction_date > date_sub((SELECT max(interaction_date) FROM {NS}.gold_topic_daily), 30) GROUP BY topic_name ORDER BY interactions DESC LIMIT 10"),
    ("Weekly safety complaints for the 2026 Aurora EV",
     f"SELECT date_trunc('WEEK', interaction_date) AS week, SUM(interactions) AS safety_interactions FROM {NS}.gold_topic_daily WHERE parent_topic = 'Vehicle Safety' AND model = 'Aurora EV' AND model_year = 2026 GROUP BY 1 ORDER BY 1"),
    ("Which dealers have the highest share of negative interactions?",
     f"SELECT dealer_name, COUNT(*) AS interactions, ROUND(100.0 * AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 1) AS negative_pct FROM {NS}.gold_interaction_insights GROUP BY dealer_name HAVING COUNT(*) >= 50 ORDER BY negative_pct DESC LIMIT 10"),
    ("How many open P1 cases are there by topic?",
     f"SELECT primary_topic, COUNT(*) AS p1_cases FROM {NS}.gold_escalation_queue WHERE priority = 'P1' GROUP BY 1 ORDER BY 2 DESC"),
]

BENCHMARKS = [
    ("How many P1 cases are in the escalation queue?",
     f"SELECT COUNT(*) AS p1_cases FROM {NS}.gold_escalation_queue WHERE priority = 'P1'"),
    ("Which active emerging issue has the biggest spike versus its baseline?",
     f"SELECT topic_name, model, model_year, peak_lift FROM {NS}.gold_emerging_issues WHERE is_alert ORDER BY peak_lift DESC LIMIT 1"),
    ("What is the average NPS by vehicle model, all model years combined?",
     f"SELECT model, ROUND(AVG(nps_score), 2) AS avg_nps FROM {NS}.gold_interaction_insights WHERE nps_score IS NOT NULL GROUP BY model ORDER BY avg_nps"),
    ("How many interactions mentioned a charge port door problem for the 2026 Aurora EV?",
     f"SELECT SUM(interactions) AS interactions FROM {NS}.gold_topic_daily WHERE topic_name = 'Charging - Charge Port Door Stuck' AND model = 'Aurora EV' AND model_year = 2026"),
    ("Which dealer has the most poor dealer experience complaints?",
     f"SELECT dealer_name, SUM(interactions) AS interactions FROM {NS}.gold_topic_daily WHERE topic_name = 'Dealer - Poor Dealer Experience' GROUP BY dealer_name ORDER BY interactions DESC LIMIT 1"),
    ("What percent of interactions are negative for each powertrain?",
     f"SELECT powertrain, ROUND(100.0 * AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 1) AS negative_pct FROM {NS}.gold_interaction_insights GROUP BY powertrain"),
]


def serialized_space():
    tables = sorted(TABLES, key=lambda t: t["identifier"])
    for t in tables:
        if "column_configs" in t:
            t["column_configs"] = sorted(t["column_configs"], key=lambda c: c["column_name"])
    return {
        "version": 2,
        "config": {"sample_questions": sorted([{"id": _id("sq" + q), "question": [q]} for q, _ in EXAMPLES[:4]], key=lambda x: x["id"])},
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": [{"id": _id("ti"), "content": INSTRUCTIONS}],
            "example_question_sqls": sorted([{"id": _id("ex" + q), "question": [q], "sql": [s]} for q, s in EXAMPLES], key=lambda x: x["id"]),
            "join_specs": [{"id": _id("j1"),
                            "left": {"identifier": f"{NS}.gold_topic_daily", "alias": "td"},
                            "right": {"identifier": f"{NS}.dim_topics", "alias": "dt"},
                            "sql": ["`td`.`topic_id` = `dt`.`topic_id`", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"]}],
        },
        "benchmarks": {"questions": sorted([{"id": _id("bm" + q), "question": [q], "answer": [{"format": "SQL", "content": [s]}]}
                                            for q, s in BENCHMARKS], key=lambda x: x["id"])},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--warehouse", required=True)
    ap.add_argument("--space-id")
    ap.add_argument("--dump", action="store_true", help="print the serialized space and exit")
    a = ap.parse_args()
    space = json.dumps(serialized_space())
    if a.dump:
        print(json.dumps(serialized_space(), indent=2)); return
    if a.space_id:
        cmd = ["databricks", "genie", "update-space", a.space_id, "--serialized-space", space,
               "--title", TITLE, "--description", DESCRIPTION, "--warehouse-id", a.warehouse]
    else:
        cmd = ["databricks", "genie", "create-space", a.warehouse, space, "--title", TITLE, "--description", DESCRIPTION]
    out = subprocess.run(cmd + ["--profile", a.profile, "-o", "json"], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stderr)
    res = json.loads(out.stdout)
    print(json.dumps({"space_id": res.get("space_id"), "title": res.get("title")}))


if __name__ == "__main__":
    main()
