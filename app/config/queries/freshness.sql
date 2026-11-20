-- Data freshness: newest interaction and when gold was last rebuilt
SELECT CAST(MAX(interaction_date) AS STRING) AS latest_interaction_date,
       CAST(MAX(refreshed_at) AS STRING) AS gold_refreshed_at,
       CAST(COUNT(*) AS INT) AS total_interactions,
       CAST(COUNT(DISTINCT interaction_date) AS INT) AS days_of_data
FROM daria_krasavina.voc_valtera.gold_interaction_insights
