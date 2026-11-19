-- SILVER sentences: the unit of classification.
-- Each transcript turn is split into sentences; speaker is kept so the scope filter
-- (customer-only) can be applied by both the rule engine and the AI classifier.

CREATE OR REFRESH STREAMING TABLE silver_sentences (
  CONSTRAINT non_empty EXPECT (length(trim(sentence_text)) > 0) ON VIOLATION DROP ROW
)
COMMENT 'One row per sentence of every call turn / survey comment. sentence_id = interaction_id-turn-sentence.'
CLUSTER BY (interaction_date)
AS
WITH turns AS (
  SELECT interaction_id, channel, created_at, language,
         t.pos AS turn_idx, t.col.speaker AS speaker, t.col.text AS turn_text
  FROM STREAM(bronze_interactions)
  LATERAL VIEW posexplode(turns) t AS pos, col
),
sentences AS (
  SELECT *, posexplode(split(trim(turn_text), '(?<=[.!?])\\s+')) AS (sentence_idx, sentence_text)
  FROM turns
)
SELECT
  concat_ws('-', interaction_id, cast(turn_idx AS STRING), cast(sentence_idx AS STRING)) AS sentence_id,
  interaction_id, channel, created_at, to_date(created_at) AS interaction_date,
  language, speaker, turn_idx, sentence_idx, trim(sentence_text) AS sentence_text
FROM sentences;
