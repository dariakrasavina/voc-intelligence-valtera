-- Negative vs. other mentions per topic group
SELECT parent_topic,
       CAST(SUM(negative_interactions) AS INT) AS negative,
       CAST(SUM(interactions) - SUM(negative_interactions) AS INT) AS neutral_or_positive
FROM daria_krasavina.voc_valtera.gold_topic_daily GROUP BY parent_topic ORDER BY SUM(interactions) DESC
