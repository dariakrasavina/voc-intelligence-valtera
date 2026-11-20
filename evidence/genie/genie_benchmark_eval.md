# Genie Agent benchmark evaluation

Agent: **Valtera VOC Insights** (`01f1e46e16d61008a7f72226f0aacb03`), created and curated by `src/notebooks/08_genie_space.py` (job task `genie_space`).
The task fails if fewer than 90% of benchmarks are correct. Final run `01f1e50d9ec918ca80cc273f6a1ea89c`: **19 / 20 correct (95%)**.

## How it got there (2026-11-20)

| Run | Result | What changed |
|---|---|---|
| 1 | 17/20 (85%) — task failed the gate | first curated version (20 benchmarks) |
| 2 | 18/20 (90%) | reference SQL aligned with equivalent answers (survey filter for NPS, no presentation-only rounding) |
| 3 | 19/20 (95%) | `peak_lift` vs `lift_vs_baseline` disambiguated in column descriptions; summary instruction no longer adds date columns |
| 4 | 19/20 (95%) | detractor reference uses the survey filter; the remaining miss is a rounding/format judgement |

## Final results

| Assessment | Question | Reasons |
|---|---|---|
| GOOD | How many P1 cases are in the escalation queue? |  |
| GOOD | How many emerging issue alerts are active? |  |
| GOOD | How many interactions came from Gold tier customers? |  |
| GOOD | How many interactions came from calls and how many from surveys? |  |
| GOOD | How many interactions mentioned a charge port door problem for the 2026 Aurora EV? |  |
| GOOD | How many interactions were there for the Strata EV, all model years? |  |
| GOOD | How many safety-related interactions were there in October 2026? |  |
| GOOD | How many tagged sentences were found only by the AI classifier and not by the rules? |  |
| GOOD | How many unexpected braking mentions were there for the 2026 Aurora EV in November 2026? |  |
| GOOD | What is the average NPS by vehicle model, all model years combined? |  |
| GOOD | What is the average escalation score of P1 cases in the queue? |  |
| GOOD | What percent of interactions are negative for each powertrain? |  |
| GOOD | What share of P1 cases in the escalation queue are vehicle safety cases? |  |
| GOOD | When was the charge port door problem on the 2026 Aurora EV first detected? |  |
| GOOD | Which 3 dealers have the most P1 cases in the escalation queue? |  |
| GOOD | Which active emerging issue has the biggest spike versus its baseline? |  |
| GOOD | Which complaint topic has the most mentions overall? |  |
| GOOD | Which dealer has the most poor dealer experience complaints? |  |
| GOOD | Which dealer region has the highest average NPS? |  |
| NEEDS_REVIEW | What is the detractor rate for surveys? | LLM_JUDGE_FORMATTING_ERROR |
