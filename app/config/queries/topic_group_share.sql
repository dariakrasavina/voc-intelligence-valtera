-- Share of topic mentions by topic group (all data)
SELECT parent_topic, CAST(SUM(interactions) AS INT) AS mentions
FROM daria_krasavina.voc_valtera.gold_topic_daily GROUP BY parent_topic ORDER BY mentions DESC
