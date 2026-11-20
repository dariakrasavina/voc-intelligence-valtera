# Genie Agent answers (space 01f1e46e16d61008a7f72226f0aacb03, captured 2026-11-20T00:23Z)

## Q: Which issues are spiking right now?

status: COMPLETED

**Generated SQL** (You want to see the list of issues that are currently spiking, including details about the topic, vehicle model, model year, the date when the spike was first detected, the highest spike size, and the number of interactions in the last 7 days.):
```sql
SELECT `topic_name`, `model`, `model_year`, `first_alert_date`, `peak_lift`, `last_7d`
FROM `daria_krasavina`.`voc_valtera`.`gold_emerging_issues`
WHERE `is_alert` = true
ORDER BY `peak_lift` DESC
```
result rows: 4

**Answer:** There are **4** issues currently flagged as spiking, all for **Aurora EV**. Examples include:
- **Charging - Charge Port Door Stuck** (2026) — first detected **2026-10-30**, peak lift **24.80**, **45** interactions in the last 7 days
- **Safety - Unexpected Braking** (2026) — first detected **2026-10-31**, peak lift **17.60**, **30** interactions in the last 7 days
- **Software - OTA Update Failure** (2026) — first detected **2026-10-31**, peak lift **7.64**, **23** interactions in the last 7 days
- **Software - Infotainment or App** (2024) — first detected **2026-11-20**, peak lift **4.40**, **11** interactions in the last 7 days
The strongest spike is **Charging - Charge Port Door Stuck**, and the newest alert is **Software - Infotainment or App**.

## Q: When was the charge port door problem on the 2026 Aurora EV first detected?

status: COMPLETED

**Generated SQL** (You want to know the first date when the issue 'Charging - Charge Port Door Stuck' was detected as an emerging problem for the 2026 Aurora EV model.):
```sql
SELECT `topic_name`, `model`, `model_year`, `first_alert_date`
FROM `daria_krasavina`.`voc_valtera`.`gold_emerging_issues`
WHERE `topic_name` = 'Charging - Charge Port Door Stuck'
  AND `model` = 'Aurora EV'
  AND `model_year` = 2026
  AND `first_alert_date` IS NOT NULL
ORDER BY `first_alert_date` ASC
LIMIT 1
```
result rows: 1

**Answer:** The **Charging - Charge Port Door Stuck** issue on the **2026 Aurora EV** was first detected on **2026-10-30**. In the visible data, **2026-10-30** is the earliest recorded alert date for **Charging - Charge Port Door Stuck** on **Aurora EV model year 2026**.

## Q: Top complaint topics for EV owners in the last 30 days

status: COMPLETED

**Generated SQL** (You want to see the top 10 complaint topics for electric vehicle (EV) owners based on the total number of interactions mentioning each topic in the last 30 days, excluding any positive feedback topics.):
```sql
WITH ranked_topics AS (
  SELECT
    `topic_name`,
    SUM(`interactions`) AS `interactions`,
    RANK() OVER (ORDER BY SUM(`interactions`) DESC) AS `topic_rank`
  FROM `daria_krasavina`.`voc_valtera`.`gold_topic_daily`
  WHERE `powertrain` = 'EV'
    AND `parent_topic` IS NOT NULL
    AND `topic_name` IS NOT NULL
    AND `parent_topic` <> 'Positive Feedback'
    AND `interaction_date` > date_sub((SELECT max(`interaction_date`) FROM `daria_krasavina`.`voc_valtera`.`gold_topic_daily`), 30)
  GROUP BY `topic_name`
)
SELECT
  `topic_name`,
  `interactions`
FROM ranked_topics
WHERE `topic_rank` <= 10
ORDER BY `topic_rank` ASC, `topic_name` ASC;
```
result rows: 10

**Answer:** In the last 30 days of available data for **EV owners**, the top complaint topic was **Charging - Charge Port Door Stuck** with **182** interactions. Examples include:
- **Charging - Charge Port Door Stuck** — **182**
- **Charging - Public Charger Failure** — **151**
- **Service - Repair Delay** — **150**
- **Software - Infotainment or App** — **150**
- **Battery - Range Loss** — **123**
Across the top 10 topics shown, charging-related issues appear most often, with **3 of the 10** top complaint topics tied to charging.

## Q: How many open P1 cases are there by topic?

status: COMPLETED

**Generated SQL** (You want to see the number of open P1 priority cases broken down by each primary topic, ordered from the topic with the most cases to the least.):
```sql
SELECT `primary_topic`, COUNT(*) AS `p1_cases`
FROM `daria_krasavina`.`voc_valtera`.`gold_escalation_queue`
WHERE `priority` = 'P1' AND `primary_topic` IS NOT NULL
GROUP BY `primary_topic`
ORDER BY `p1_cases` DESC
```
result rows: 3

**Answer:** There are **3** topics shown for **P1 cases**, led by **Safety - Unexpected Braking** with **131** cases, followed by **Safety - Warning Light or Airbag** with **128**, and **Safety - Driver Assist Malfunction** with **98**. Across these results, all listed P1 cases are **safety-related**, with counts ranging from **98** to **131**.

**Answer:** Would you like to see the count of P1 cases by topic including only those created in the last 30 days instead?

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

**Answer:** Among dealers with at least **50** interactions, **Ironwood Valtera** has the highest share of negative interactions at **97.3%**, followed closely by **Granite Valtera** at **97.2%** and **Blue Mesa Valtera** at **96.8%**. Examples include:
- **Ironwood Valtera** — **97.3%** negative across **294** interactions
- **Granite Valtera** — **97.2%** negative across **289** interactions
- **Blue Mesa Valtera** — **96.8%** negative across **344** interactions
- **Cedar Ridge Valtera** — **95.9%** negative across **314** interactions
- **Stonebridge Valtera** — **95.9%** negative across **294** interactions
Across the 10 dealers shown, negative interaction share is consistently very high, ranging from **94.7%** to **97.3%**.
