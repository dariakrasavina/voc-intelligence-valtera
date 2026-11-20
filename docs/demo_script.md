# Demo script: AI roleplay (20–30 min)

**Room:** *Business:* VP Customer Experience & Vehicle Quality (funds the decision).
*Technical:* data platform architect (has to run it).
**Structure:** tell (what I'll show and why it matters) → show → tell (what it means for the business). Lead with the outcome.

---

## 0 · Set up the room (2 min) — TELL
> "Valtera gets about 240K calls and surveys a month. Today a vendor tool tags them with keyword rules, and Quality
> gets a report at month-end. So a defect introduced by a software update reaches Safety 3–5 weeks after
> customers start calling, and about 1 in 5 complaints is never tagged because people don't use the keywords.
> In the next 20 minutes I'll show three things: we caught a real safety signal **2–6 days** after an OTA release,
> every serious case now has an owner, and anyone can ask questions in plain English. Then we'll look at cost and how
> it runs."

Check in: *"Is time-to-detect the metric your team is measured on, or is it cost per contact?"* Adjust emphasis.

## 1 · Overview: the safety signal (5 min)
- **TELL:** "This is the screen your quality lead opens every morning."
- **SHOW:** KPI row (with period and source) → red **emerging issues** card (4 alerts) → Aurora EV trend chart.
  - If asked about the 4th alert (2026 Ridgeback Hybrid infotainment, 6.9×): "Real spikes happen at low volume. The
    rule raises it and an analyst decides; that's why it doesn't escalate on its own." 
  - "OTA 4.2 went out Oct 28. The charge-port-door alert fired **Oct 30**, OTA failure **Oct 31** and unexpected braking
    **Nov 3**: 9.6×, 6.5× and 10.4× their normal weekly volume."
- **TELL (business):** "Under the monthly report you'd have seen this at the end of November. That's about 4 weeks of
  rollout to roughly 6,000 more vehicles, about $0.9M in service and goodwill by our estimate, plus the recall and brand risk."
- **TELL (technical):** "The rule is checked every day, per topic × model × model year: at least 10 interactions in 7 days
  and at least 4× the previous 4 weeks. Simple enough for Safety to audit, and the threshold is one line of SQL."

## 2 · Escalation queue: from signal to owner (5 min)
- **SHOW:** filter P1 → open an unexpected-braking case → AI summary + recommended action → set *Acknowledged*,
  assignee "Safety investigation team", add a note → **Save to Lakebase** → the status count updates.
- **TELL (business):** "Every P1 has an owner and an audit trail. Your agents read a one-line summary instead of the transcript."
- **TELL (technical):** "The queue is a Delta table synced to Lakebase Postgres, so reads take milliseconds. Agent updates go
  into a separate app-owned schema with an audit log, and Lakehouse Sync streams them straight back into the lakehouse, so
  Monitoring and Genie can answer 'how many P1 safety cases are still open?' within seconds. The app's service principal
  can only read the gold tables: no names, emails, phones or VINs."
- **SHOW (optional):** Monitoring → "How escalation cases are handled" now shows the case you just saved.

## 3 · Ask Genie (4 min)
- **SHOW:** "When was the charge port door problem on the 2026 Aurora EV first detected?" → **2026-10-30**.
  Then "Which dealers have the highest share of negative interactions?" Open **Generated SQL**.
- **TELL:** "Your analysts stop waiting on report requests. The SQL is always visible, so the numbers can be checked,
  and Genie only sees governed tables without PII."

## 4 · Why trust the tagging (4 min)
- **SHOW:** Topics page (pick "Charging - Charge Port Door Stuck" → quotes, rules vs. AI), then Monitoring → tagging accuracy.
- **TELL:** "Keyword rules are perfectly explainable but miss every paraphrase: 77.9% recall. AI classification with
  the same plain-language topic definitions catches them. Together: **99.4% recall, 96.1% precision**. We measure this
  on every run against labelled data, so if quality drops we see it."
- **Technical detail:** each rule tag stores the words that triggered it; ai_classify returns a confidence and a rationale.

## 5 · Cost, operations, next steps (3 min) — TELL
- "One serverless job. It starts by itself when your export lands, and it's incremental. Yesterday's re-run processed 0 old files, and today's run processed only today's 70 interactions."
- "We classify each *distinct* sentence once: 4,018 AI calls instead of 11,953, and a new day only pays for its new wording (43 calls). Sentiment
  uses a small trained model, so there's no per-call cost."
- "30/60/90: run on 3 months of your real exports and migrate your vendor rule set → analysts label 500 sentences and we
  tune → run alongside the vendor for a month, then retire the license."
- **Ask:** "Can we get a sample export and two of your analysts for the 30-day pilot?"

---

## Objections: be ready to switch altitude

| From | Objection | Answer |
|---|---|---|
| Business | "What does it cost?" | Estimated $60–90K/yr in Databricks consumption vs. ~$600K license; caching and the trained model keep AI cost flat as volume grows. |
| Business | "How fast can we see value?" | 30-day pilot on your exports; the alert and queue work from day one, since the rules migrate as data. |
| Business | "What if the AI is wrong on a safety case?" | AI only adds recall; every safety tag can be checked (rule terms or AI rationale), summaries are marked "verify", and the human owner decides. |
| Business | "Will my analysts lose control of the taxonomy?" | No. They own `category_model.json`: keywords and plain-language definitions drive both the rules and the AI. |
| Technical | "Data quality?" | Auto Loader with schema hints and rescued data, expectations at bronze and silver (drop missing IDs or empty transcripts, flag bad powertrain / region values), AUTO CDC for customer, vehicle and dealer changes, ground-truth evaluation each run. |
| Technical | "Security / PII?" | PII tagged and masked in UC; gold, Genie and the app never see it; the app's service principal has SELECT on gold only. |
| Technical | "Integration with our case system?" | The queue is in Postgres: the case system can read it directly, or we push via an API in phase 3. |
| Technical | "Scale?" | Serverless pipeline and jobs; classification work grows with *distinct* sentences, not volume. The rule engine runs in parallel as a PySpark `pandas_udf`. |
| Technical | "Why not one LLM for everything?" | Cost, determinism and auditability. Rules give exact explanations; ai_classify handles nuance; ai_query with a specific LLM stays an option. |
| Technical | "Is it really incremental?" | Yes. Auto Loader tracks processed files: the rebuild wrote 6,166 rows, the next day's file added only +70 (Delta history in `evidence/incremental_run.md`). |
