-- SILVER interactions: each interaction enriched with vehicle, dealer and customer
-- context (no PII columns), ready for the gold layer and Genie.

CREATE OR REFRESH MATERIALIZED VIEW silver_interactions
COMMENT 'Interaction header joined to vehicle (model, powertrain, model year), dealer (name, region) and customer tier. No PII.'
AS SELECT
  i.interaction_id, i.channel, i.created_at, to_date(i.created_at) AS interaction_date,
  i.call_reason, i.duration_sec, i.nps_score, i.customer_id, i.vin,
  v.model, v.powertrain, v.model_year,
  d.dealer_id, d.dealer_name, d.region AS dealer_region, d.state AS dealer_state,
  c.loyalty_tier, c.region AS customer_region,
  size(i.turns) AS turn_count,
  concat_ws(' ', transform(filter(i.turns, t -> t.speaker = 'customer'), t -> t.text)) AS customer_text
FROM bronze_interactions i
LEFT JOIN bronze_vehicles v ON i.vin = v.vin
LEFT JOIN bronze_dealers  d ON i.dealer_id = d.dealer_id
LEFT JOIN silver_customers c ON i.customer_id = c.customer_id;
