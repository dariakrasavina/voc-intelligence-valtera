# Genie Agent benchmark evaluation

Space `01f1e46e16d61008a7f72226f0aacb03` (Valtera VOC Insights). Benchmarks are defined in `src/genie/genie_space.py`.

## Run 1: initial instructions

result: **3 / 6 correct** (eval run `01f1e4731e0111918d65b6c41c14ebef`)

| Question | Assessment | Reasons |
|---|---|---|
| What percent of interactions are negative for EVs vs ICE vehicles? | BAD | RESULT_MISSING_ROWS, LLM_JUDGE_INCORRECT_METRIC_CALCULATION |
|  ↳ Genie SQL | `SELECT CASE WHEN `powertrain` = 'EV' THEN 'EV' ELSE 'ICE' END AS `vehicle_type`, COUNT(DISTINCT CASE WHEN `sentiment` = 'negative' THEN `interaction_id` END) AS `negative_interactions`, COUNT(DISTINCT `interaction_id`) AS `total_interactions`, ROUND(try_divide(100.0 * COUNT(DISTINCT CASE WHEN `sentiment` = 'negative' THEN `interaction_id` END),COUNT(DISTINCT `interaction_id`)), 1) AS `negative_pct` | |
| Which topic and vehicle had the biggest spike versus its baseline? | GOOD |  |
| How many interactions mentioned a charge port door problem for the 2026 Aurora EV? | GOOD |  |
| How many P1 cases are in the escalation queue? | GOOD |  |
| What is the average NPS by vehicle model? | BAD | RESULT_EXTRA_ROWS, LLM_JUDGE_MISSING_OR_INCORRECT_AGGREGATION |
|  ↳ Genie SQL | `SELECT `model`, `model_year`, AVG(`nps_score`) AS `avg_nps` FROM `daria_krasavina`.`voc_valtera`.`gold_interaction_insights` WHERE `model` IS NOT NULL   AND `model_year` IS NOT NULL   AND `nps_score` IS NOT NULL GROUP BY `model`, `model_year` ORDER BY `avg_nps` DESC, `model` ASC, `model_year` ASC` | |
| Which dealer has the most poor dealer experience complaints? | BAD | RESULT_MISSING_COLUMNS, LLM_JUDGE_INCORRECT_METRIC_CALCULATION |
|  ↳ Genie SQL | `WITH `dealer_complaints` AS (   SELECT     `dealer_name`,     COUNT(DISTINCT `interaction_id`) AS `poor_dealer_experience_complaints`   FROM `daria_krasavina`.`voc_valtera`.`gold_interaction_insights`   WHERE `primary_topic` = 'Dealer - Poor Dealer Experience'     AND `dealer_name` IS NOT NULL   GROUP BY `dealer_name` ), `ranked_dealers` AS (   SELECT     `dealer_name`,     `poor_dealer_experience` | |

## Run 2: after fixing instructions (powertrain values, topic-mention counting, model-year aggregation)

result: **5 / 6 correct** (eval run `01f1e473d246133e93fcbaec9117e1cf`)

| Question | Assessment | Reasons |
|---|---|---|
| What percent of interactions are negative for each powertrain? | GOOD |  |
| How many interactions mentioned a charge port door problem for the 2026 Aurora EV? | GOOD |  |
| How many P1 cases are in the escalation queue? | GOOD |  |
| What is the average NPS by vehicle model, all model years combined? | NEEDS_REVIEW | LLM_JUDGE_FORMATTING_ERROR |
| Which dealer has the most poor dealer experience complaints? | GOOD |  |
| Which active emerging issue has the biggest spike versus its baseline? | GOOD |  |

