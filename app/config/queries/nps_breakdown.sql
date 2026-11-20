-- Survey NPS: promoters (9-10), passives (7-8), detractors (0-6) by vehicle model
SELECT model,
       CAST(SUM(CASE WHEN nps_score >= 9 THEN 1 ELSE 0 END) AS INT) AS promoters,
       CAST(SUM(CASE WHEN nps_score BETWEEN 7 AND 8 THEN 1 ELSE 0 END) AS INT) AS passives,
       CAST(SUM(CASE WHEN nps_score <= 6 THEN 1 ELSE 0 END) AS INT) AS detractors,
       CAST(ROUND(100.0 * (AVG(CASE WHEN nps_score >= 9 THEN 1.0 ELSE 0.0 END) - AVG(CASE WHEN nps_score <= 6 THEN 1.0 ELSE 0.0 END))) AS INT) AS nps
FROM daria_krasavina.voc_valtera.gold_interaction_insights WHERE channel = 'survey' GROUP BY model ORDER BY nps
