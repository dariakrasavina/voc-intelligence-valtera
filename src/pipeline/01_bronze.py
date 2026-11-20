"""
BRONZE: raw files from the contact-center / survey export land in a UC volume.

Every bronze table is ingested with Databricks **Auto Loader** (`cloudFiles`): it tracks which files it has
already processed, so each pipeline update reads only NEW files (the daily export) instead of re-reading
history. Schema hints pin the important types; anything unexpected goes to `_rescued_data` instead of
failing the load.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

LANDING = spark.conf.get("landing_path")


def auto_loader(folder, schema_hints=None):
    reader = (spark.readStream.format("cloudFiles")
              .option("cloudFiles.format", "json")
              .option("cloudFiles.inferColumnTypes", "true"))
    if schema_hints:
        reader = reader.option("cloudFiles.schemaHints", schema_hints)
    return (reader.load(f"{LANDING}/{folder}")
            .withColumn("source_file", F.col("_metadata.file_path"))
            .withColumn("ingested_at", F.current_timestamp()))


@dp.table(comment="Raw contact-center calls and post-service surveys (one row per interaction), ingested incrementally with Auto Loader.")
@dp.expect_all_or_drop({"valid_id": "interaction_id IS NOT NULL", "has_turns": "size(turns) > 0"})
@dp.expect("valid_channel", "channel IN ('call', 'survey')")
def bronze_interactions():
    return auto_loader("interactions",
                       "interaction_id STRING, channel STRING, created_at TIMESTAMP, customer_id STRING, vin STRING, "
                       "dealer_id STRING, language STRING, call_reason STRING, duration_sec INT, nps_score INT, "
                       "turns ARRAY<STRUCT<speaker: STRING, text: STRING>>")


@dp.table(comment="Customer change records from the CRM export (upserts, sequenced by updated_at). Contains PII.")
@dp.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
def bronze_customers():
    return auto_loader("customers", "customer_id STRING, updated_at TIMESTAMP, loyalty_tier STRING")


@dp.table(comment="Vehicle registry records: VIN, model, powertrain, model year, selling dealer.")
@dp.expect_or_drop("valid_vin", "vin IS NOT NULL")
def bronze_vehicles():
    return auto_loader("vehicles", "vin STRING, model_year INT, sold_date DATE")


@dp.table(comment="Dealer network reference records.")
@dp.expect_or_drop("valid_dealer_id", "dealer_id IS NOT NULL")
def bronze_dealers():
    return auto_loader("dealers")
