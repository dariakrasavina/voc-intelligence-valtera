"""
SILVER sentences: the unit of classification.

Each transcript turn is split into sentences; the speaker is kept so the scope filter (customer side only)
can be applied by both the rule engine and ai_classify. Streaming, so only new interactions are split.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

SENTENCE_SPLIT = r"(?<=[.!?])\s+"


@dp.table(comment="One row per sentence of every call turn / survey comment. sentence_id = interaction_id-turn-sentence.",
          cluster_by=["interaction_date"])
@dp.expect_or_drop("non_empty", "length(trim(sentence_text)) > 0")
def silver_sentences():
    turns = (spark.readStream.table("bronze_interactions")
             .select("interaction_id", "channel", "created_at", "language",
                     F.posexplode("turns").alias("turn_idx", "turn")))
    sentences = turns.select(
        "*", F.posexplode(F.split(F.trim(F.col("turn.text")), SENTENCE_SPLIT)).alias("sentence_idx", "raw_sentence"))
    return sentences.select(
        F.concat_ws("-", "interaction_id", F.col("turn_idx").cast("string"), F.col("sentence_idx").cast("string"))
         .alias("sentence_id"),
        "interaction_id", "channel", "created_at", F.to_date("created_at").alias("interaction_date"), "language",
        F.col("turn.speaker").alias("speaker"), "turn_idx", "sentence_idx",
        F.trim("raw_sentence").alias("sentence_text"))
