-- What customers actually said about one topic
-- @param topic STRING
SELECT sentence_text, detected_by, matched_terms, ai_confidence, ai_rationale, channel, CAST(created_at AS STRING) AS created_at
FROM daria_krasavina.voc_valtera.gold_sentence_topics
WHERE topic_name = :topic
ORDER BY created_at DESC
LIMIT 25
