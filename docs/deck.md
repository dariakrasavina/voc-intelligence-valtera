---
title: "Valtera Motors · VOC Intelligence"
subtitle: "From customer complaints to safety signals in days, not weeks"
note: "Valtera Motors is a fictional automaker. All data is synthetic. Value figures are estimates for an OEM of this size, to be validated with the customer."
---

# 1 · Valtera Motors: catch safety issues in days, not at month-end

**Audience:** Executive sponsor — VP Customer Experience & Vehicle Quality. Domain owner — VOC Analytics lead.
Technical stakeholder — Data platform architect.

**The ask:** replace the vendor text-analytics tool with one governed Databricks flow that tags every call and
survey, flags emerging safety issues automatically, and puts the right cases in front of the right team.

**Headline outcome (estimated, year 1): ~$1.6M** — vendor license retired, analyst time returned, and safety
signals detected about 4 weeks earlier.

---

# 2 · Today: a monthly report on last month's problems

- About 180K contact-center calls and 60K post-service surveys a month go into a **vendor text-analytics tool**.
- Topics come from **keyword rules**, so paraphrases are missed. In our sample, **1 in 5 complaints** is phrased
  in a way the keyword rules never match ("that little door where you plug in won't budge").
- Quality and Safety get a **month-end export**. Nobody owns the case after it is tagged.
- Data is copied out of the lakehouse, so it cannot be joined with vehicle, dealer or OTA data, and it is not governed.

**Cost of the status quo:** about $600K/yr license, about 5 analysts maintaining rules and reviewing tags, and
safety signals that surface 3–5 weeks after customers start calling.

---

# 3 · Outcome in the buyer's KPIs

| KPI | Today | With VOC Intelligence | Basis |
|---|---|---|---|
| Time to detect an emerging safety issue | ~30 days (month-end report) | **2–3 days** after OTA 4.2 | measured on the seeded OTA 4.2 issue |
| Complaints correctly topic-tagged (recall) | 79.8% (keyword rules) | **100%** (rules + ai_classify) | measured vs. ground truth |
| Vendor text-analytics license | ~$600K/yr | $0 (Databricks consumption ≈ $60–90K/yr) | estimate |
| Analyst hours on rule upkeep and tag review | ~5 FTE | ~2.5 FTE (≈ $300K/yr returned) | estimate |
| Vehicles exposed to a bad OTA before rollback | full rollout | ~6,000 fewer at 1,500/week × 4 weeks earlier (≈ $0.9M at $150/vehicle in service + goodwill) | estimate |
| P1 safety case response | no owner | P1 queue with AI summary, owner and audit trail | built |

**Executive sponsor:** about $1.6M a year, plus risk reduction on safety recalls.
**Domain owner:** one taxonomy you can edit without code, with every tag explained.

---

# 4 · Demo storyline (what you will see)

1. **Overview:** "4 emerging issues". Three are the 2026 Aurora EV after OTA 4.2 (Oct 28): charge-port door, unexpected
   braking, OTA failure. One is a small infotainment spike, which is why alerts go to an analyst. The rule fired on **Oct 30 for charge-port door and Oct 31 for unexpected braking, 2–3 days after release**.
2. **Escalation queue:** the P1 braking cases with an AI case summary and recommended action. Assign one to the
   safety investigation team and add a note; it is saved to Lakebase with an audit log.
3. **Ask Genie:** "When was the charge port door problem on the 2026 Aurora EV first detected?" and "Which dealers
   have the highest share of negative interactions?", with the generated SQL shown.
4. **Model quality:** rules vs. AI vs. combined, scored against ground truth.

---

# 5 · One integrated flow on Databricks

```
Contact-center + survey export ──► UC Volume (landing)
   └─► Lakeflow Declarative Pipeline in Python (Auto Loader → bronze, AUTO CDC customers/vehicles/dealers, sentence split, expectations)
        └─► Unity Catalog silver (governed: PII tags, masking function, secure view)
             ├─► Rule engine (explainable, unit-tested)       ┐
             ├─► ai_classify v2.1 (plain-language topics)      ├─► gold: sentence topics, interaction insights,
             └─► Sentiment model (MLflow, UC @champion)       ┘          topic daily, emerging issues, metric view
                  └─► gold_escalation_queue ──► Lakebase synced table ──► Databricks App (case write-back to Lakebase)
                  └─► Genie Agent "Valtera VOC Insights" ──────────────────► Ask Genie tab in the same app
```

One Lakeflow Job runs it end to end and incrementally: it starts by itself when a new export lands (file-arrival trigger). Pipeline, job and app are Databricks Asset Bundles;
the Genie Agent, grants and Lakebase setup are scripted. All of it is in Git.

---

# 6 · Classification: rules for precision, AI for recall

| Method | Precision | Recall | F1 |
|---|---|---|---|
| Keyword rule engine | 100.0%¹ | 79.8% | 88.8% |
| ai_classify (v2.1) | 99.9% | 97.4% | 98.7% |
| **Rules + AI combined** | **99.9%** | **100%** | **99.9%** |

¹ On synthetic data the rule vocabulary matches the generator, so rule precision is perfect by construction. Expect lower on real data.

- The rules catch **100%** of complaints that use the expected vocabulary and **0%** of paraphrases.
- ai_classify catches **100%** of the paraphrases, using the same plain-language topic definitions the
  business already writes.
- Every rule tag stores the words that triggered it, so the counts are explainable to Quality and Legal.

---

# 7 · Trusted and governed by default

- **Unity Catalog:** PII columns tagged (`pii`), masked unless the reader is in `valtera_voc_pii_readers`.
  Gold tables, Genie and the app never see names, emails, phones or VINs.
- **Model governance:** the sentiment model is tracked in MLflow and registered in UC (`voc_sentiment_model@champion`).
- **Measured, not assumed:** every run scores the classifiers against ground truth and writes the metrics to a table.
- **Genie Agent built by the job:** column descriptions, joins, measures, filters, example SQL and 20 benchmarks are version-controlled; benchmarks went from 85% to 95% after curation, and the job fails below 90%.

---

# 8 · Cost and scale choices

- **97.8% fewer LLM calls:** 15,821 customer sentences needed only 350 ai_classify calls (one per *distinct* sentence,
  cached). The second full run made **0** new calls, so daily increments only pay for new wording.
- **Zero-token sentiment:** an LLM labels a sample once, and a small trained model scores everything after that.
- **Serverless everywhere:** pipeline, job and SQL. Lakebase scales to zero when the app is idle.
- Escalation reads are served from **Lakebase** (milliseconds), and analytics from the SQL warehouse.

---

# 9 · Decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| Keep a rule engine next to the AI | Explainable, deterministic control; vendor rules can be migrated as-is | Two methods to maintain (the same taxonomy file drives both) |
| ai_classify over ai_query + an LLM | Purpose-built, confidence scores, no prompt to own | Fixed Databricks model; ai_query is an option if a specific LLM is needed |
| Train a sentiment model on LLM weak labels | No per-call cost at volume, owned in UC | Weak labels ≠ human truth; next step is a human-labeled gold set |
| Daily alert rule (≥10 in 7 days, ≥4× baseline) | Simple, explainable to Safety | Thresholds need tuning on real volume; a statistical model could come later |
| Lakebase for the queue | Low-latency reads and transactional write-back | Synced table is triggered, not continuous (minutes, not seconds) |
| MERGE the queue into Delta (never replace) | Lakebase sync streams only the changed cases | Needs a stable key (case_id) and a change check |

---

# 10 · Next 30 / 60 / 90 days

- **30:** run on 3 months of real exports in a Valtera workspace; migrate the vendor rule set into the taxonomy file.
- **60:** analysts label 500 sentences to make a gold set; retrain sentiment and tune ai_classify confidence and alert thresholds.
- **90:** run alongside the vendor for one month, then switch over and retire the license. Connect the P1 queue to the case system.
