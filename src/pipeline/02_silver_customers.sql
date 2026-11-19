-- SILVER customers: AUTO CDC keeps exactly one current row per customer (SCD1).
-- Later CRM batches (tier upgrades, email changes) overwrite older values in order.

CREATE OR REFRESH STREAMING TABLE silver_customers
COMMENT 'Current customer profile (SCD Type 1 via AUTO CDC). Contains PII: first_name, last_name, email, phone -> masked for non-privileged users.';

CREATE FLOW silver_customers_cdc AS AUTO CDC INTO silver_customers
FROM STREAM(bronze_customers)
KEYS (customer_id)
SEQUENCE BY updated_at
COLUMNS * EXCEPT (op, source_file, _rescued_data)
STORED AS SCD TYPE 1;
