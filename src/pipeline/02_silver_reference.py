"""
SILVER reference data: one CURRENT row per customer, vehicle and dealer.

AUTO CDC (SCD Type 1) applies each new export batch in order, so a later CRM / registry file
(e.g. a loyalty-tier upgrade, a vehicle re-assigned to another dealer) overwrites the older values.
Customers are sequenced by their `updated_at`; vehicles and dealers by ingestion time (their exports
carry no change timestamp).
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

EPOCH = F.lit("1970-01-01 00:00:00").cast("timestamp")

# --- customers -----------------------------------------------------------------------------------
dp.create_streaming_table(
    name="silver_customers",
    comment="Current customer profile (SCD Type 1 via AUTO CDC). Contains PII: first_name, last_name, email, "
            "phone -> masked for non-privileged users through customers_secure.")
dp.create_auto_cdc_flow(
    target="silver_customers", source="bronze_customers", keys=["customer_id"], sequence_by="updated_at",
    stored_as_scd_type=1, except_column_list=["op", "source_file", "ingested_at", "_rescued_data"],
    name="silver_customers_cdc")


# --- vehicles ------------------------------------------------------------------------------------
@dp.temporary_view()
@dp.expect("valid_powertrain", "powertrain IN ('EV', 'HYBRID', 'ICE')")
@dp.expect("valid_model_year", "model_year BETWEEN 2015 AND 2030")
def vehicles_changes():
    return (spark.readStream.table("bronze_vehicles")
            .withColumn("_seq", F.coalesce("ingested_at", EPOCH)))


dp.create_streaming_table(
    name="silver_vehicles",
    comment="Current vehicle registry (SCD Type 1 via AUTO CDC): one row per VIN with model, powertrain, model year "
            "and selling dealer.")
dp.create_auto_cdc_flow(
    target="silver_vehicles", source="vehicles_changes", keys=["vin"], sequence_by="_seq", stored_as_scd_type=1,
    except_column_list=["source_file", "ingested_at", "_seq", "_rescued_data"], name="silver_vehicles_cdc")


# --- dealers -------------------------------------------------------------------------------------
@dp.temporary_view()
@dp.expect("valid_region", "region IN ('Midwest', 'Northeast', 'South', 'West')")
def dealers_changes():
    return (spark.readStream.table("bronze_dealers")
            .withColumn("_seq", F.coalesce("ingested_at", EPOCH)))


dp.create_streaming_table(
    name="silver_dealers",
    comment="Current dealer network (SCD Type 1 via AUTO CDC): one row per dealer with name, region and state.")
dp.create_auto_cdc_flow(
    target="silver_dealers", source="dealers_changes", keys=["dealer_id"], sequence_by="_seq", stored_as_scd_type=1,
    except_column_list=["source_file", "ingested_at", "_seq", "_rescued_data"], name="silver_dealers_cdc")
