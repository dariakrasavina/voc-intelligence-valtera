# Genie Agent answers (space 01f1e46e16d61008a7f72226f0aacb03, captured 2026-11-19T23:22Z)

## Q: Which issues are spiking right now?

status: COMPLETED

**Generated SQL** (You want to see the list of issues that are currently spiking, showing the topic name, vehicle model, model year, the date when the spike was first detected, the highest lift value during the spike, and the number of interactions in the last 7 days for each issue. The results are ordered by the highest spike intensity.):
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
result rows: 3

**Answer:** The issues currently spiking are all on the **2026 Aurora EV**: **Charging - Charge Port Door Stuck** (first detected **2026-10-30**, peak lift **24.80**, **42** interactions in the last 7 days), **Safety - Unexpected Braking** (first detected **2026-10-31**, peak lift **17.60**, **33** last-7-day interactions), and **Software - OTA Update Failure** (first detected **2026-10-31**, peak lift **7.64**, **19** last-7-day interactions). Across the **3** active alerts shown, charging is the strongest spike, and all three issues were first detected within a two-day window at the end of October 2026.

## Q: When was the charge port door problem on the 2026 Aurora EV first detected?

status: COMPLETED

**Generated SQL** (You want to know the earliest date when the problem with the charge port door on the 2026 Aurora EV was first detected as an emerging issue.):
```sql
SELECT MIN(`first_alert_date`) AS `first_detected_date`
FROM `daria_krasavina`.`voc_valtera`.`gold_emerging_issues`
WHERE `model` = 'Aurora EV'
  AND `model_year` = 2026
  AND `topic_name` = 'Charging - Charge Port Door Stuck'
  AND `first_alert_date` IS NOT NULL
```
result rows: 1

**Answer:** The charge port door issue for the **2026 Aurora EV** was first detected on **2026-10-30**. Based on the available result, **2026-10-30** is also the earliest detected date for the topic **Charging - Charge Port Door Stuck** on the **2026 Aurora EV**.

## Q: Top complaint topics for EV owners in the last 30 days

status: COMPLETED

**Generated SQL** (You want to see the top complaint topics for electric vehicle (EV) owners in the last 30 days, excluding any positive feedback topics. The results show the total number of interactions for each complaint topic, ranked from most to least interactions.):
```sql
WITH `topic_counts` AS (
  SELECT
    `topic_name`,
    SUM(`interactions`) AS `interactions`,
    RANK() OVER (ORDER BY SUM(`interactions`) DESC) AS `topic_rank`
  FROM `daria_krasavina`.`voc_valtera`.`gold_topic_daily`
  WHERE `powertrain` = 'EV'
    AND `parent_topic` <> 'Positive Feedback'
    AND `interaction_date` > date_sub((SELECT max(`interaction_date`) FROM `daria_krasavina`.`voc_valtera`.`gold_topic_daily`), 30)
    AND `topic_name` IS NOT NULL
  GROUP BY `topic_name`
)
SELECT
  `topic_name`,
  `interactions`
FROM `topic_counts`
ORDER BY `topic_rank` ASC, `topic_name` ASC
```
result rows: 14

**Answer:** Examples include these top complaint topics for **EV owners** in the last 30 days:
- **Charging - Charge Port Door Stuck:** **174** interactions
- **Service - Repair Delay:** **156**
- **Charging - Public Charger Failure:** **152**
- **Software - Infotainment or App:** **147**
- **Dealer - Poor Dealer Experience:** **126**
Across the **14** topics shown, charging-related issues appear repeatedly among the highest-volume complaints.

## Q: How many open P1 cases are there by topic?

status: COMPLETED

**Generated SQL** (You want to see the number of open P1 cases broken down by each primary topic, ordered from the topic with the most cases to the least.):
```sql
SELECT `primary_topic`, COUNT(*) AS `p1_cases`
FROM `daria_krasavina`.`voc_valtera`.`gold_escalation_queue`
WHERE `priority` = 'P1' AND `primary_topic` IS NOT NULL
GROUP BY `primary_topic`
ORDER BY `p1_cases` DESC
```
result rows: 3

**Answer:** There are **3** topics shown for P1 cases, led by **Safety - Warning Light or Airbag** with **130** cases, followed by **Safety - Unexpected Braking** with **129**, and **Safety - Driver Assist Malfunction** with **99**. The counts are tightly clustered at the top, with only a **1-case** gap between the first two topics.

## Q: Which dealers have the highest share of negative interactions?

status: COMPLETED

**Generated SQL** (You want to see the top 10 dealers ranked by the highest percentage of negative customer interactions, considering only those dealers with at least 50 interactions.):
```sql
SELECT
  `dealer_name`,
  COUNT(DISTINCT `interaction_id`) AS `interactions`,
  ROUND(100.0 * AVG(CASE WHEN `sentiment` = 'negative' THEN 1 ELSE 0 END), 1) AS `negative_pct`
FROM `daria_krasavina`.`voc_valtera`.`gold_interaction_insights`
WHERE `dealer_name` IS NOT NULL
GROUP BY `dealer_name`
HAVING COUNT(DISTINCT `interaction_id`) >= 50
ORDER BY `negative_pct` DESC, `interactions` DESC
LIMIT 10
```
result rows: 10

**Answer:** Examples include:
- **Ironwood Valtera** — **97.2%** negative across **289** interactions
- **Granite Valtera** — **97.2%** negative across **285** interactions
- **Blue Mesa Valtera** — **96.8%** negative across **343** interactions
- **Stonebridge Valtera** — **96.2%** negative across **289** interactions
- **Cedar Ridge Valtera** — **95.9%** negative across **314** interactions
Across the 10 dealers shown, negative share is consistently very high, ranging from **94.7%** to **97.2%**.

**Answer:** Would you like to see dealers ranked by other measures of negative experience, such as low NPS scores or high escalation scores, instead of sentiment alone?
