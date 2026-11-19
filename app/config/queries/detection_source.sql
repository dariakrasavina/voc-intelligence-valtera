-- How each topic tag was found: rule engine only, ai_classify only, or both
SELECT detected_by, CAST(COUNT(*) AS INT) AS tagged_sentences
FROM daria_krasavina.voc_valtera.gold_sentence_topics GROUP BY detected_by ORDER BY tagged_sentences DESC
