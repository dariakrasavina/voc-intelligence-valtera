-- BRONZE: raw files from the contact-center / survey export land in a UC volume.
-- Auto Loader (STREAM read_files) picks up only NEW files on each update, so the
-- daily export is processed incrementally instead of re-reading 90 days of history.

CREATE OR REFRESH STREAMING TABLE bronze_interactions (
  CONSTRAINT valid_id      EXPECT (interaction_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_channel EXPECT (channel IN ('call', 'survey')),
  CONSTRAINT has_turns     EXPECT (size(turns) > 0) ON VIOLATION DROP ROW
)
COMMENT 'Raw contact-center calls and post-service surveys (one row per interaction), ingested incrementally with Auto Loader.'
AS SELECT
  *,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/interactions',
  format => 'json',
  schemaHints => 'interaction_id STRING, channel STRING, created_at TIMESTAMP, customer_id STRING, vin STRING, dealer_id STRING, language STRING, call_reason STRING, duration_sec INT, nps_score INT, turns ARRAY<STRUCT<speaker: STRING, text: STRING>>'
);

CREATE OR REFRESH STREAMING TABLE bronze_customers
COMMENT 'Customer change records from the CRM export (upserts, sequenced by updated_at).'
AS SELECT *, _metadata.file_path AS source_file
FROM STREAM read_files('${landing_path}/customers', format => 'json',
  schemaHints => 'customer_id STRING, updated_at TIMESTAMP, loyalty_tier STRING');

CREATE OR REFRESH STREAMING TABLE bronze_vehicles
COMMENT 'Vehicle registry: VIN, model, powertrain, model year, selling dealer.'
AS SELECT *, _metadata.file_path AS source_file
FROM STREAM read_files('${landing_path}/vehicles', format => 'json',
  schemaHints => 'vin STRING, model_year INT, sold_date DATE');

CREATE OR REFRESH STREAMING TABLE bronze_dealers
COMMENT 'Dealer network reference data.'
AS SELECT *, _metadata.file_path AS source_file
FROM STREAM read_files('${landing_path}/dealers', format => 'json');
