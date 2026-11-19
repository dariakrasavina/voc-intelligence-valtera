-- Active emerging issues: topic x vehicle where the daily alert rule (>=10 interactions in 7 days and >=4x the prior 4-week weekly average) fired in the last 30 days
SELECT topic_name, parent_topic, model, CAST(model_year AS INT) AS model_year,
       CAST(first_alert_date AS STRING) AS first_alert_date, peak_lift,
       CAST(last_7d AS INT) AS last_7d, CAST(as_of_date AS STRING) AS as_of_date
FROM daria_krasavina.voc_valtera.gold_emerging_issues
WHERE is_alert
ORDER BY peak_lift DESC
LIMIT 10
