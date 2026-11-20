-- How each topic group was detected: keyword rules, ai_classify, or both
SELECT parent_topic,
       CAST(SUM(CASE WHEN detected_by = 'both' THEN 1 ELSE 0 END) AS INT) AS both_methods,
       CAST(SUM(CASE WHEN detected_by = 'rules' THEN 1 ELSE 0 END) AS INT) AS rules_only,
       CAST(SUM(CASE WHEN detected_by = 'ai' THEN 1 ELSE 0 END) AS INT) AS ai_only
FROM daria_krasavina.voc_valtera.gold_sentence_topics GROUP BY parent_topic ORDER BY both_methods + rules_only + ai_only DESC
