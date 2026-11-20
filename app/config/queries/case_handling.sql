-- How escalation cases are being handled (statuses saved in the app, streamed back via Lakehouse Sync)
SELECT priority, status, CAST(COUNT(*) AS INT) AS cases,
       ROUND(AVG(CASE WHEN first_action_at IS NOT NULL THEN (unix_timestamp(first_action_at) - unix_timestamp(created_at)) / 3600.0 END), 1) AS avg_hours_to_first_action
FROM daria_krasavina.voc_valtera.gold_case_status GROUP BY ALL ORDER BY priority, status
