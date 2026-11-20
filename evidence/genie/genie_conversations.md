# Genie Agent answers (space 01f1e46e16d61008a7f72226f0aacb03, captured 2026-11-20T19:54Z)

## Q: Which issues are spiking right now?

status: COMPLETED

**Generated SQL** (You want to see which complaint topics are currently spiking, showing the vehicle model and model year for each, along with the date when the spike was first detected, the size of the biggest spike, and the number of interactions in the last 7 days.):
```sql
SELECT `topic_name`, `model`, `model_year`, `first_alert_date`, `peak_lift`, `last_7d`
FROM `daria_krasavina`.`voc_valtera`.`gold_emerging_issues`
WHERE `is_alert` = true
  AND `topic_name` IS NOT NULL
  AND `model` IS NOT NULL
  AND `model_year` IS NOT NULL
  AND `peak_lift` IS NOT NULL
ORDER BY `peak_lift` DESC
```
result rows: 4

**Answer:** From the alert data in the **2026-08-22 to 2026-11-20** period, there are **4 issues** currently flagged as spiking. Some of the top issues are:
- **Safety - Unexpected Braking** on **2026 Aurora EV** — peak lift **10.40**, with **21** mentions in the last 7 days, first alerted **2026-11-03**
- **Charging - Charge Port Door Stuck** on **2026 Aurora EV** — peak lift **9.60**, with **32** mentions in the last 7 days, first alerted **2026-10-30**
- **Software - Infotainment or App** on **2026 Ridgeback Hybrid** — peak lift **6.86**, with **0** mentions in the last 7 days, first alerted **2026-10-26**
- **Software - OTA Update Failure** on **2026 Aurora EV** — peak lift **6.50**, with **17** mentions in the last 7 days, first alerted **2026-10-31**
The strongest spike is **Unexpected Braking**, while **Aurora EV** accounts for **3 of the 4** current alerts.

## Q: When was the charge port door problem on the 2026 Aurora EV first detected?

status: COMPLETED

**Generated SQL** (You want to know the earliest date when the issue of the charge port door being stuck was first detected for the 2026 Aurora EV model.):
```sql
SELECT MIN(`first_alert_date`) AS `first_detected`
FROM `daria_krasavina`.`voc_valtera`.`gold_emerging_issues`
WHERE `topic_name` = 'Charging - Charge Port Door Stuck'
  AND `model` = 'Aurora EV'
  AND `model_year` = 2026
  AND `first_alert_date` IS NOT NULL
```
result rows: 1

**Answer:** For the **2026 Aurora EV**, the **Charging - Charge Port Door Stuck** issue was first detected on **2026-10-30**. Within the available data range of **2026-08-22 to 2026-11-20**, **2026-10-30** is the earliest recorded alert date for this issue.

## Q: Top complaint topics for EV owners in the last 30 days

status: COMPLETED

**Generated SQL** ():
```sql
SELECT topic_name, SUM(interactions) AS mentions FROM daria_krasavina.voc_valtera.gold_topic_daily WHERE powertrain = :powertrain AND parent_topic <> 'Positive Feedback' AND interaction_date BETWEEN :start_date AND :end_date GROUP BY topic_name ORDER BY mentions DESC LIMIT 10
```
result rows: 10

**Answer:** For **EV owners** in the **last 30 days** ending **2026-11-20**, the top complaint topics are shown below from the 10 returned results. Examples include:
- **Service - Repair Delay:** **111** mentions
- **Charging - Charge Port Door Stuck:** **110** mentions
- **Charging - Public Charger Failure:** **110** mentions
- **Billing - Payment or Financing Issue:** **105** mentions
- **Software - Infotainment or App:** **102** mentions
Charging-related issues appear repeatedly among the top complaints, indicating they are a major concern for EV owners in this period.

## Q: How many open P1 cases are there by topic?

status: COMPLETED

**Generated SQL** (You want to see the number of open P1 cases broken down by each primary topic.):
```sql
SELECT `primary_topic` AS `topic`, COUNT(*) AS `open_p1_cases`
FROM `daria_krasavina`.`voc_valtera`.`gold_case_status`
WHERE `priority` = 'P1'
  AND `status` = 'Open'
  AND `primary_topic` IS NOT NULL
GROUP BY ALL
ORDER BY `open_p1_cases` DESC, `topic` ASC
```
result rows: 3

**Answer:** From the available results, there are **3** open **P1** case topics shown. In the data provided, **Safety - Warning Light or Airbag** has **117** open P1 cases, followed by **Safety - Unexpected Braking** with **89**, and **Safety - Driver Assist Malfunction** with **60**; all shown open P1 cases are safety-related topics.

## Q: Which dealers have the highest share of negative interactions?

status: COMPLETED

**Generated SQL** (You want to see the top 10 dealers ranked by the highest percentage of negative customer interactions from August 22, 2026, to November 20, 2026.):
```sql
SELECT
  `dealer_name`,
  COUNT(DISTINCT `interaction_id`) AS `interactions`,
  100.0 * AVG(CASE WHEN `sentiment` = 'negative' THEN 1.0 ELSE 0.0 END) AS `negative_share_pct`
FROM `daria_krasavina`.`voc_valtera`.`gold_interaction_insights`
WHERE `dealer_name` IS NOT NULL
GROUP BY `dealer_name`
HAVING COUNT(DISTINCT `interaction_id`) >= 50
ORDER BY `negative_share_pct` DESC, `interactions` DESC, `dealer_name` ASC
LIMIT 10
```
result rows: 10

**Answer:** From the available data for **2026-08-22 to 2026-11-20**, the dealers with the highest share of negative interactions are shown below among dealers with at least **50** interactions.

Some of the top values are:
- **Summit Valtera** — **67.1%** negative across **362** interactions
- **Lakeshore Valtera** — **65.4%** negative across **381** interactions
- **Sunset Valtera** — **63.4%** negative across **306** interactions
- **Westfield Valtera** — **63.0%** negative across **276** interactions
- **Harbor Valtera** — **62.8%** negative across **226** interactions

Across the 10 dealers shown, negative share ranges from **61.4%** to **67.1%**, with **Summit Valtera** highest.
