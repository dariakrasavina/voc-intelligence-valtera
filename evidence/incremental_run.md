# Incremental ingestion (Auto Loader) on the final, noisy dataset

Source: Delta history of the streaming tables (`evidence/query_results/incremental_delta_history.json`).

| table | version | time | what happened | rows written |
|---|---|---|---|---|
| bronze_interactions | v7 | 2026-11-20 14:01 | full refresh after the data was regenerated (90 days, noisy transcripts) | 6,166 |
| bronze_interactions | v8 | 2026-11-20 14:40 | `scripts/land_export.sh … daily 2026-11-20` landed **one** new file | **+70** |
| silver_sentences | v11 | 2026-11-20 14:01 | sentence split of the rebuilt data | 39,454 |
| silver_sentences | v12 | 2026-11-20 14:41 | only the new day's sentences | **+480** |

Earlier versions (v2/v3 and v3/v5) are the first, cleaner dataset from 2026-11-19, which showed the same behaviour: the
90-day load wrote 6,046 rows, a second run over the same 90 files wrote **0** (no streaming update at all), and the next
day wrote +70.

Downstream, the new day cost **43** ai_classify calls (only sentences whose wording was not already cached under the
current topic definitions). Job run `544525181135495`: 9/9 tasks SUCCESS (`evidence/job_run_summary.txt`).
