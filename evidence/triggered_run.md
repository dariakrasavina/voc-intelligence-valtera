# Job triggers: file arrival + 8 a.m. schedule

## `valtera-voc-end-to-end` (job 791845510507972)

trigger:
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

## `valtera-voc-daily-8am` (job 954517480636777)

schedule:
```json
{
  "pause_status": "UNPAUSED",
  "quartz_cron_expression": "0 0 8 * * ?",
  "timezone_id": "America/New_York"
}
```

## Verification (2026-11-20)

1. `valtera-voc-export-simulator` landed today's export at 09:36:52 (America/New_York).
2. The file-arrival trigger started `valtera-voc-end-to-end` ~2.5 min later (2 min settle time, as configured).
3. `valtera-voc-daily-8am` was started once manually to prove it launches the processing job (it is scheduled for 08:00 daily).

| run | started by | result | tasks |
|---|---|---|---|
| `910785349295240` | RUN_JOB_TASK | SUCCESS | lakeflow_ingest:SUCCESS, ai_classify:SUCCESS, governance:SUCCESS, rule_tagging:SUCCESS, sentiment_model:SUCCESS, gold_and_alerts:SUCCESS, evaluate:SUCCESS, lakebase_sync:SUCCESS |
| `51524864464018` | FILE_ARRIVAL | SUCCESS | lakeflow_ingest:SUCCESS, ai_classify:SUCCESS, governance:SUCCESS, rule_tagging:SUCCESS, sentiment_model:SUCCESS, gold_and_alerts:SUCCESS, evaluate:SUCCESS, lakebase_sync:SUCCESS |
