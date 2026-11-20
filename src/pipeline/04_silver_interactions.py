"""
SILVER interactions: each interaction enriched with its vehicle, dealer and customer context
(no PII columns), ready for the gold layer and Genie. Built from the silver reference tables.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    comment="Interaction header joined to silver_vehicles (model, powertrain, model year), silver_dealers (name, region) "
            "and silver_customers (tier, region). No PII.")
def silver_interactions():
    i = spark.read.table("bronze_interactions").alias("i")
    v = spark.read.table("silver_vehicles").select("vin", "model", "powertrain", "model_year")
    d = spark.read.table("silver_dealers").select(
        "dealer_id", "dealer_name", F.col("region").alias("dealer_region"), F.col("state").alias("dealer_state"))
    c = spark.read.table("silver_customers").select(
        "customer_id", "loyalty_tier", F.col("region").alias("customer_region"))
    customer_text = F.concat_ws(" ", F.transform(F.filter("turns", lambda t: t.speaker == "customer"), lambda t: t.text))
    return (i.join(v, "vin", "left").join(d, "dealer_id", "left").join(c, "customer_id", "left")
            .select("interaction_id", "channel", "created_at", F.to_date("created_at").alias("interaction_date"),
                    "call_reason", "duration_sec", "nps_score", "customer_id", "vin",
                    "model", "powertrain", "model_year",
                    "dealer_id", "dealer_name", "dealer_region", "dealer_state",
                    "loyalty_tier", "customer_region",
                    F.size("turns").alias("turn_count"), customer_text.alias("customer_text")))
