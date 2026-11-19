-- Dealers with the highest share of negative interactions (min 50 interactions)
SELECT dealer_name, dealer_region, CAST(COUNT(*) AS INT) AS interactions,
       ROUND(100.0 * AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 1) AS negative_pct,
       CAST(SUM(CASE WHEN array_contains(topics, 'Dealer - Poor Dealer Experience') THEN 1 ELSE 0 END) AS INT) AS poor_experience
FROM daria_krasavina.voc_valtera.gold_interaction_insights
GROUP BY ALL HAVING COUNT(*) >= 50
ORDER BY poor_experience DESC LIMIT 8
