-- How customers feel, week by week (interactions by sentiment)
SELECT CAST(date_trunc('WEEK', interaction_date) AS DATE) AS week,
       CAST(SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS INT) AS negative,
       CAST(SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) AS INT) AS neutral,
       CAST(SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) AS INT) AS positive
FROM daria_krasavina.voc_valtera.gold_interaction_insights GROUP BY 1 ORDER BY 1
