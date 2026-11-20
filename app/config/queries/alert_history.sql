-- Every topic x vehicle the alert rule has ever flagged
SELECT topic_name, model, CAST(model_year AS INT) AS model_year, CAST(first_alert_date AS STRING) AS first_alert_date,
       peak_lift, CAST(last_7d AS INT) AS last_7d, is_alert
FROM daria_krasavina.voc_valtera.gold_emerging_issues WHERE first_alert_date IS NOT NULL ORDER BY first_alert_date
