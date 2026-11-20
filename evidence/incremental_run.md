# Incremental daily run (2026-11-20)

Job run `615261678774193` with `generate_mode=daily, day=2026-11-20`, started after the full backfill run `327620437213971`.
The generator landed **one** new file (`landing/interactions/interactions_20261120.json`): {'mode': 'daily', 'interactions_written': 70, 'labels': 94, 'dealers': 20, 'customers': 3200, 'vehicles': 3200}

## Auto Loader processed only the new file (Delta history of the streaming tables)

| table | version | time (UTC-5) | rows written |
|---|---|---|---|
| bronze_interactions | v2 | 2026-11-19 17:55:50 | 6046 |
| bronze_interactions | v3 | 2026-11-19 18:45:30 | 70 |
| silver_sentences | v3 | 2026-11-19 17:55:57 | 32433 |
| silver_sentences | v5 | 2026-11-19 18:45:39 | 399 |

* First run (17:55): full 90-day backfill, 6,046 interactions / 32,433 sentences.
* Second full run (18:09, backfill mode re-landing the same 90 files): **no streaming update was written**. Auto Loader had already processed those files.
* Daily run (18:45): **+70 interactions / +399 sentences**, the new day only.

## Downstream

* ai_classify: 0 new ai_classify calls, cache size 350 (new day's wording was already cached).
* Lakebase sync: gold_escalation_queue 438 rows, Lakebase 433 rows.

## Task results

| task | result | duration |
|---|---|---|
| land_export | SUCCESS | 42s |
| lakeflow_ingest | SUCCESS | 94s |
| ai_classify | SUCCESS | 61s |
| governance | SUCCESS | 55s |
| rule_tagging | SUCCESS | 74s |
| sentiment_model | SUCCESS | 75s |
| gold_and_alerts | SUCCESS | 45s |
| evaluate | SUCCESS | 25s |
| lakebase_sync | SUCCESS | 76s |
