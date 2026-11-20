# File-arrival trigger on `valtera-voc-end-to-end`

```json
{
  "pause_status": "UNPAUSED",
  "file_arrival": {
    "url": "/Volumes/daria_krasavina/voc_valtera/landing/",
    "min_time_between_triggers_seconds": 300,
    "wait_after_last_change_seconds": 120
  }
}
```

Verification (2026-11-20, current version of the job, 9 tasks): a new file `landing/dealers/dealers_redelivery_20261120.json`
(a re-delivery of the dealer reference file) was copied into the landing volume at 15:23:09 America/New_York. The trigger
started run `341185253280121` about 2 minutes later, with no manual start.

| run | started by | result |
|---|---|---|
| `341185253280121` | FILE_ARRIVAL | SUCCESS |

| task | result |
|---|---|
| lakeflow_ingest | SUCCESS |
| ai_classify | SUCCESS |
| governance | SUCCESS |
| rule_tagging | SUCCESS |
| sentiment_model | SUCCESS |
| gold_and_alerts | SUCCESS |
| evaluate | SUCCESS |
| genie_space | SUCCESS |
| lakebase_sync | SUCCESS |

Effect of the re-delivered file: `bronze_dealers` = 40 rows (raw, append-only: the 20 dealers landed twice), `silver_dealers` = 20 rows
(AUTO CDC keeps one current row per dealer, so the duplicate delivery does not duplicate anything downstream).

Note: after the trigger had been paused and re-enabled, files that were *overwritten* in place did not start a run; a new file
did. Exports always arrive as new files (`interactions_YYYYMMDD.json`), so this matches the real flow.
Earlier verification of the same trigger (before the Genie task and the data rebuild): run `51524864464018`, FILE_ARRIVAL, SUCCESS.
