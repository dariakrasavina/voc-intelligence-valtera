-- Every topic the classifiers found: volume, negativity, and how it was detected
WITH t AS (
  SELECT topic_name, parent_topic,
         COUNT(DISTINCT interaction_id) AS interactions,
         COUNT(*) AS tagged_sentences,
         SUM(CASE WHEN detected_by = 'rules' THEN 1 ELSE 0 END) AS by_rules_only,
         SUM(CASE WHEN detected_by = 'ai' THEN 1 ELSE 0 END) AS by_ai_only,
         SUM(CASE WHEN detected_by = 'both' THEN 1 ELSE 0 END) AS by_both,
         max_by(sentence_text, coalesce(ai_confidence, 0)) AS example_quote
  FROM daria_krasavina.voc_valtera.gold_sentence_topics GROUP BY ALL),
neg AS (
  SELECT topic_name, SUM(negative_interactions) AS negative_interactions, SUM(interactions) AS mentions
  FROM daria_krasavina.voc_valtera.gold_topic_daily GROUP BY topic_name)
SELECT t.topic_name, t.parent_topic, CAST(t.interactions AS INT) AS interactions,
       ROUND(100.0 * n.negative_interactions / n.mentions, 1) AS negative_pct,
       CAST(t.by_rules_only AS INT) AS by_rules_only, CAST(t.by_ai_only AS INT) AS by_ai_only, CAST(t.by_both AS INT) AS by_both,
       ROUND(100.0 * t.by_ai_only / t.tagged_sentences, 1) AS ai_only_pct, t.example_quote
FROM t JOIN neg n USING (topic_name)
ORDER BY interactions DESC
