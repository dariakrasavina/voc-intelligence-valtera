-- Top complaint topics in the last 30 days
WITH b AS (SELECT max(interaction_date) AS d FROM daria_krasavina.voc_valtera.gold_topic_daily)
SELECT topic_name, CAST(SUM(interactions) AS INT) AS interactions,
       CAST(SUM(negative_interactions) AS INT) AS negative_interactions
FROM daria_krasavina.voc_valtera.gold_topic_daily CROSS JOIN b
WHERE interaction_date > date_sub(b.d, 30) AND parent_topic <> 'Positive Feedback'
GROUP BY topic_name ORDER BY interactions DESC LIMIT 10
