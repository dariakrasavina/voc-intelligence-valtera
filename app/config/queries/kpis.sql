-- Headline KPIs for the last 30 days of data
WITH b AS (SELECT max(interaction_date) AS d FROM daria_krasavina.voc_valtera.gold_interaction_insights)
SELECT
  CAST(COUNT(*) AS INT) AS interactions,
  ROUND(100.0 * AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 1) AS negative_pct,
  ROUND(100.0 * AVG(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END), 1) AS positive_pct,
  CAST(SUM(CASE WHEN is_safety THEN 1 ELSE 0 END) AS INT) AS safety_interactions,
  CAST(SUM(CASE WHEN priority = 'P1' THEN 1 ELSE 0 END) AS INT) AS p1_cases,
  ROUND(AVG(nps_score), 1) AS avg_nps,
  CAST(MAX(b.d) AS STRING) AS as_of_date
FROM daria_krasavina.voc_valtera.gold_interaction_insights CROSS JOIN b
WHERE interaction_date > date_sub(b.d, 30)
