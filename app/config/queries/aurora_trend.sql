-- Weekly interactions for the 2026 Aurora EV: the two topics that spiked after OTA 4.2 (released 2026-10-28)
SELECT CAST(date_trunc('WEEK', interaction_date) AS DATE) AS week,
       CAST(SUM(CASE WHEN topic_name = 'Charging - Charge Port Door Stuck' THEN interactions ELSE 0 END) AS INT) AS charge_port_door,
       CAST(SUM(CASE WHEN topic_name = 'Safety - Unexpected Braking' THEN interactions ELSE 0 END) AS INT) AS unexpected_braking,
       CAST(SUM(CASE WHEN topic_name = 'Software - OTA Update Failure' THEN interactions ELSE 0 END) AS INT) AS ota_update_failure
FROM daria_krasavina.voc_valtera.gold_topic_daily
WHERE model = 'Aurora EV' AND model_year = 2026
GROUP BY 1 ORDER BY 1
