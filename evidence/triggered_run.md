# File-arrival trigger on `valtera-voc-end-to-end`

```json
{
  "file_arrival": {
    "min_time_between_triggers_seconds": 300,
    "url": "/Volumes/daria_krasavina/voc_valtera/landing/",
    "wait_after_last_change_seconds": 120
  },
  "pause_status": "UNPAUSED"
}
```

Verification (2026-11-20): `scripts/land_export.sh daria_k_sandbox daily 2026-11-20` copied today's export into the
landing volume at 09:57:42 America/New_York. The trigger started the job about 2 minutes later, with no manual start.

| run | started by | result |
|---|---|---|
| `51524864464018` | FILE_ARRIVAL | SUCCESS |

| task | result |
|---|---|
| lakeflow_ingest | SUCCESS |
| ai_classify | SUCCESS |
| governance | SUCCESS |
| rule_tagging | SUCCESS |
| sentiment_model | SUCCESS |
| gold_and_alerts | SUCCESS |
| evaluate | SUCCESS |
| lakebase_sync | SUCCESS |
