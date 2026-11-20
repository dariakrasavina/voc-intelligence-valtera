# Demo script v2: AI roleplay (Yoodli)

**Room:** *Business:* VP Customer Experience & Vehicle Quality (funds it). *Technical:* data platform architect (runs it).
**Format:** tell → show → tell. Lead with the outcome. Every claim has something on screen behind it.
**Deck:** `docs/Valtera_VOC_Intelligence_deck_v2.pdf` · **App:** Overview · Topics · Escalation queue · Monitoring · Ask Genie
**Honesty rule:** for anything probed, say what it covers and what it doesn't: *"In our test…"*, never *"proven"*.
Valtera is fictional and the data is synthetic. Say so once at the start, then don't apologise for it.

---

## 0 · Before the session (10 min)

- [ ] App open and **warmed up**: click through all 5 tabs once, so charts and the SQL warehouse are already running.
- [ ] Ask Genie once ("Which issues are spiking right now?"), so it's warm too, then click **New conversation**.
- [ ] Escalation queue filtered to **P1**, case **I2026111900007** (Acknowledged, Safety investigation team) ready to show.
- [ ] Deck open on slide 1, in a second window.
- [ ] **Fallback recording** of the 5-tab walkthrough ready (QuickTime screen recording, about 3 min). Use it if anything is slow.
- [ ] Two clocks: **presenting time** (target 17 min) and **whole session** (hard stop 30 min).

**Never click during the demo:**
- Don't run the job, land a file or trigger a pipeline update; a run takes about 10 minutes.
- Never "Full refresh" the pipeline.
- Don't edit `category_model.json` or Genie instructions live.
- Don't open Lakebase or Catalog admin pages; use the evidence slides instead.
- In the queue, only change the case you prepared. Don't mass-edit.

---

## 1 · Run of show, slide by slide (deck v2, about 17 min presenting)

Each block: **On the slide** (what they're looking at, so you can explain it) · **Say** · **Show** (when to switch to
the app) · **Land** (what it means for them). Answer first, detail second. Keep the architecture detail for the technical persona.

---

### Slide 1 · Title: "Valtera Motors hears a defect in 2 days, not 30." (0:00–0:45)
- **On the slide:** the headline result, the audience (VP CX & Vehicle Quality), and the products used (Lakeflow, Unity Catalog, AI Functions, Lakebase, Apps, Genie).
- **Say:** "Thanks for the time. Valtera is fictional and the data is synthetic, but everything you'll see is running on Databricks. The short version: you'd hear about a defect in 2 days, not at month-end."
- **Set the stage (the guide's first step):** "Your goal, as I understand it, is to catch quality and safety issues earlier and stop losing complaints in a monthly report. Today I'll show the result, a real example, the live app, then value and a pilot. **What would you most like me to cover?**" Then **wait, and use their answer**: spend more time on whatever they name.

### Slide 2 · Executive summary: "From a monthly report to a daily safety signal." (0:45–2:00)
- **On the slide:** four numbers, plus problem → solution → outcome along the bottom.
  - **$4.0M** year-1 value (ESTIMATE)
  - **2 days** to detect (MEASURED)
  - **99.4%** of complaints tagged (MEASURED)
  - **318** cases with an owner (BUILT)
- **Say:** "Four numbers. The value is an estimate. Detection and coverage are measured from the running system. 318 serious cases now have an owner. The green and orange tags tell you which is which: measured versus estimated."
- **Land (executive):** "Earlier signal, fewer missed complaints, and a clear owner for every serious case."

### Slide 3 · The problem: "240,000 customer voices a month, read once a month." (2:00–3:00)
- **On the slide:** three failures.
  - **1 in 5** complaints missed by keyword rules (1,320 of 5,978).
  - **3–5 weeks** before Safety sees a defect, while the update keeps rolling out to about 1,500 vehicles a week.
  - **0** safety cases with an owner.
  - Bottom row, the cost of the status quo: ~$600K license, ~5 FTE, ~$0.9M exposure per bad OTA (ESTIMATE).
- **Say:** "Customers don't use your keywords: 'that little door where you plug in won't budge' never matches a rule. And because it's a month-end export, a bad software update keeps shipping for weeks."
- **Land (domain owner):** "Your team is working from a report that's both late and incomplete."

### Slide 4 · Real example: "OTA 4.2: the signal was in the calls 2 days after release." (3:00–4:30) → **demo stop 1**
- **On the slide:** a timeline. OTA 4.2 shipped **Oct 28**. Alerts fired for:
  - charge-port door on **Oct 30** (9.6×, 2 days)
  - OTA failure on **Oct 31** (6.5×, 3 days)
  - unexpected braking on **Nov 3** (10.4×, 6 days, P1 safety)
  The vendor's month-end report would have landed **Nov 30**: **31 days later**. The alert rule is at least 10 mentions in 7 days and at least 4× the 4-week baseline.
- **Say:** "The first alert came 2 days after release, and the safety alert 6 days after: 27 days before the report. That's about 4 weeks of rollout you could have paused."
- **Show (app · Overview):** the emerging-issues card (4 alerts) and the Aurora EV trend chart. "This is the screen your Quality lead opens every morning."
- **Land:** "A 4th, unplanted spike was flagged too. That's why an alert opens an analyst review; it doesn't escalate on its own."

### Slide 5 · Architecture: "One governed flow, from call transcript to case owner." (4:30–5:30)
- **On the slide:** five stages, 01 Land → 02 Ingest → 03 Govern → 04 Understand → 05 Act:
  - 01 Land: UC Volumes
  - 02 Ingest: Lakeflow, Auto Loader, AUTO CDC
  - 03 Govern: Unity Catalog, PII masks
  - 04 Understand: AI Functions, MLflow, metric view
  - 05 Act: Lakebase, Apps, Genie
  Also: one Lakeflow Job (9 tasks, serverless, 9/9 SUCCESS), and the closed loop through Lakehouse Sync.
- **Say (business, one sentence):** "One platform, one copy of the data, from the call file to the person who owns the case."
- **Say (technical, if they're engaged):** "A new export landing in a volume triggers the job. Auto Loader ingests only the new files. Agent updates stream back to the lakehouse with Lakehouse Sync. Everything deploys from Git as bundles."

### Slide 6 · Gap → product → result: "Each Databricks product closes one specific gap." (5:30–6:30)
- **On the slide:** six rows. Each one maps a Valtera gap to a Databricks product and a result:
  - keyword misses → ai_classify → **77.9% → 99.4%** recall
  - month-end export → Lakeflow + file-arrival trigger → **~30 → 2 days**
  - data stuck in a vendor tool → Unity Catalog → **0 PII beyond silver**
  - nobody owns the case → Lakebase + Apps → **318 cases routed**
  - questions waiting on reports → Genie → **19/20 benchmarks**
  - AI cost growing with volume → cache + trained model → **−66% LLM calls**
- **Say:** "If you remember one slide, this is it. Every gap you have maps to one product, and to one result we measured."
- **Land:** pick the 1–2 rows that match what they asked for on slide 1.

### Slide 7 · Classification quality: "Rules for precision, AI for recall, both for coverage." (6:30–8:00) → **demo stop 2**
- **On the slide:** bars measured against **5,978 labelled complaint topics**:
  - Recall: rules 77.9% · AI 97.4% · **combined 99.4%**
  - Precision: rules 100%¹ · AI 96.1% · combined 96.1%
  - Two examples: AI catches a paraphrase ("I plug it in at the house…", confidence 0.78, with its reason), and rules explain a tag ("phantom braking").
  - Footnote ¹: rule precision is 100% only because the synthetic vocabulary matches the rules.
- **Say:** "Rules are exact and explainable, but they miss paraphrases. AI catches those, and it tells you why. Run both and you find 99.4% of complaints. We re-measure this on every run."
- **Show (app · Topics):** pick *Charging - Charge Port Door Stuck* and show one quote found *AI only* (with its reason) and one with keywords. Then the donut and weekly trend charts.
- **Land (domain owner):** "Your analysts can see the exact evidence behind every count, and they own the topic definitions, with no code."

### Slide 8 · Escalation queue: "Every P1 safety case now has an owner and an audit trail." (8:00–10:30) → **demo stop 3, the one live workflow**
- **On the slide:** case **I2026111900007**: P1, 2026 Aurora EV, Riverbend Valtera. It shows the AI case summary, the recommended action, the status (Acknowledged), the assignee (Safety investigation team) and the audit line. Also: **318 cases**, Delta = Lakebase rows (**318 = 318**, checked every run), and **0 PII fields** visible to the app.
- **Say:** "An agent reads one line instead of a transcript, gets a recommended next step, and takes ownership."
- **Show (app · Escalation queue → then Monitoring):**
  1. Filter P1 and open a braking case.
  2. Set status, assignee and a note, then **Save to Lakebase**. The status count updates.
  3. Switch to **Monitoring → How escalation cases are handled**: the update is already there.
- **Say (technical):** "The queue is synced from Delta to Lakebase Postgres for millisecond reads. Agent updates go into an app-owned schema with an audit log, and Lakehouse Sync streams them back to Unity Catalog within seconds."
- **Land:** "Nothing waits for a month-end export, and your reporting sees how every case is handled."

### Slide 9 · Ask Genie: "Quality leads ask in plain English and see the SQL." (10:30–12:00) → **demo stop 4**
- **On the slide:** two real Genie answers:
  - "First detected on 2026-10-30", with its generated SQL.
  - "4 alerts; strongest: unexpected braking, 10.4×".
  - Three proof points: trust by design (gold tables only, no PII, SQL always shown), curated as code (rebuilt on every job run), and benchmarked (85% → 95%, the job fails below 90%).
- **Show (app · Ask Genie):** ask "When was the charge port door problem on the 2026 Aurora EV first detected?" and open the Generated SQL.
- **Say:** "Your analysts stop waiting on report requests, and they can check exactly how each answer was computed."
- **Checkpoint:** if you're past **12:00** here, skip slide 10 and go to slide 11.

### Slide 10 · Governance & cost: "Governed by default, and two-thirds fewer AI calls." (12:00–13:00)
- **On the slide:**
  - Left: the masked customer table as a non-PII reader sees it (K******, +******). PII is tagged and masked; the model is in UC as `@champion`; every run is scored against ground truth.
  - Right: **11,953** sentences → **4,018** AI calls (−66%) → **43** for a new day, plus zero-token sentiment from a trained model (accuracy 0.987).
- **Say (technical):** "Security is in Unity Catalog, not in the app. And AI cost grows with new wording, not with volume."

### Slide 11 · Value: "~$4.0M of year-1 value on ~$75K of consumption." (13:00–14:30)
- **On the slide:** four estimated lines:
  - $2.3M revenue protected (6,000 owners × 8% defection avoided × $4,800)
  - $0.9M OTA exposure avoided
  - $0.5M license net of consumption
  - $0.3M analyst time
  - Total $4.0M; not counted: recall and brand risk.
- **Say:** "Everything on this slide is an estimate to validate in the pilot. The conservative part is $1.7M: license, analyst time and OTA exposure. The other $2.3M depends on how many affected owners you'd otherwise lose. That's the assumption I'd test first."
- **Land (executive):** "Even the conservative case is well over 10× the consumption cost."

### Slide 12 · Before & after: "Before and after, in the KPIs Quality is measured on." (14:30–15:15)
- **On the slide:** eight KPIs, each marked MEASURED, BUILT or ESTIMATE:
  - detection: ~30 → 2–6 days
  - recall: 77.9% → 99.4% at 96.1% precision
  - P1 owner: none → 318 cases
  - questions: backlog → Genie at 95%
  - LLM calls: −66%
  - run cost: ~$600K → ~$60–90K
  - vehicles exposed: ~6,000 fewer
  - revenue protected: ~$2.3M
- **Say:** "This is the scorecard I'd propose we track together in the pilot."

### Slide 13 · Next 90 days: "Pilot on real exports, then retire the vendor tool." (15:15–16:30)
- **On the slide:** three phases, each with a measurable exit test:
  - **Day 30:** 3 months of real exports; replay your last real OTA issue.
  - **Day 60:** 500 analyst-labelled sentences; recall ≥ 95% and precision ≥ 90%.
  - **Day 90:** run in parallel for a month, then retire the license; Safety signs off on the P1 queue.
  - Also: what Valtera brings, what Databricks brings, and what we'll measure.
- **Say:** "Same code, same job, in your workspace. Each phase has an exit test, so you're never committing to more than 30 days at a time."

### Slide 14 · The ask: "Next step: a 30-day pilot on 3 months of your real exports." (16:30–17:00)
- **On the slide:** the ask (a sample export, two analysts, a Safety lead), plus the three headline numbers: **2 days, not 30** · **99.4% of complaints** · **~$4.0M year 1 (est.)**.
- **Say:** the close in section 4, then **pause**.

**Time budget:** about 17 min presenting, about 10 min for questions. Two clocks: presenting (target 17) and the whole session (hard stop 30).
**If the AI starts wrapping up early:** jump straight to the close in section 4, from wherever you are.

---

## 2 · Answers to prepare (from the field guide)

### "What does success look like after the pilot?"
**Answer:** "Four measurable targets we agree in week one; these are my proposals until you agree them:
1. **Earlier detection:** replay your last real OTA or quality issue; we flag it at least 3 weeks before your current report did.
2. **Coverage:** on a 500-sentence gold set your analysts label, recall ≥ 95% and precision ≥ 90%.
3. **Ownership:** every P1 safety case gets a first action within 24 hours, for 4 weeks running.
4. **Cost:** dollars per 1,000 interactions, measured in the pilot, below what the vendor tool costs today."
**Evidence:** slide 13 (pilot plan). **Limit:** targets are proposals until the customer agrees them.

### "What does it cost?"
**Answer:** "It's consumption, not a license. You pay for what runs:
- serverless compute for the pipeline and job (about 10 minutes per daily run in our test),
- tokens for AI functions, only on *new* wording, because each distinct sentence is classified once (4,018 calls for 11,953 sentences, and 43 for a new day),
- Lakebase, which scales to zero when the app is idle,
- the app's compute.
We size it at roughly $60–90K a year, against a ~$600K license. But that's an estimate from a prototype: **the pilot measures the real cost per 1,000 interactions on your volume**. We weigh it against $1.7M a year in cost and risk avoided, or $4.0M if we count the revenue from owners we don't lose."
**Evidence:** slide 10 (AI cost) and slide 11 (value). **Limit:** prototype cost is not production cost, and all dollar figures are estimates.

### "What if your results disagree with my team's?"
**Answer:** "Then we've found something to calibrate, and that's a win. How it works:
- **Who and when:** in the pilot, two of your analysts review a sample every week. They see every tag *with its evidence*: the keywords for a rule tag, or the confidence and reason for an AI tag (Topics page).
- **How each difference is resolved:**
  - If our tag is wrong, the fix is a change to the taxonomy file: a keyword, or a topic definition. Change a definition and every sentence is re-classified automatically on the next run.
  - If your team's tag was wrong, it goes into the gold set.
  - If both readings are reasonable, we split or rename the topic.
- **Measured:** every run re-scores both methods against the gold set, so you see the agreement trend."
**Evidence:** the Topics page (how each tag was found) and the Monitoring page (accuracy). **Limit:** tested on synthetic data with generated labels only. There's no in-app "disagree" button yet; in the pilot, disagreements go through the weekly review.

### "Can I trust the AI?"
**Answer:** "Be clear about what it decides and what it doesn't:
- **AI does:** suggests topics (with a confidence and a reason), writes one-line case summaries, and answers questions in Genie.
- **AI doesn't:** close cases, contact customers or escalate on its own. Alerts come from a simple, auditable rule (at least 10 mentions in 7 days and at least 4× baseline), and every case is owned by a person.
- **How it's checked:**
  - Every run scores rules, AI and the combination against labelled data; in our test that's 96% precision and 99% recall combined.
  - AI tags below 0.6 confidence are dropped.
  - Genie must pass 20 benchmark questions; the job fails below 90%.
  - Every Genie answer shows its SQL, and case summaries are marked 'verify'.
- **Final call:** your analysts and the case owner."
**Evidence:** slide 7 (classification quality) and the Genie benchmarks. **Limit:** judged on a synthetic, labelled sample. Real accuracy is a pilot target (≥ 95% recall, ≥ 90% precision).

### "What happens with a late or corrupted file?"
**Answer:**
- **Late file:** "The job starts when the file arrives (a file-arrival trigger). There's no fixed schedule to miss, and it processes only the new file. In our test, a new day added 70 interactions and nothing else."
- **Re-sent or duplicate file:** "Safe. Auto Loader processes each file once, and AUTO CDC keeps one current row per customer, vehicle and dealer. In our test, a re-delivered dealer file put 40 rows in bronze, but silver still had 20."
- **Corrupted content:**
  - Data-quality expectations drop rows with no ID or an empty transcript, and flag invalid values such as channel, powertrain, region or loyalty tier.
  - Unexpected fields go to a `_rescued_data` column instead of failing the load.
  - The pipeline's event log records pass and fail counts per rule.
- **Visible failure and safe rerun:** "The job fails if the Lakebase copy doesn't match the lakehouse, or if Genie drops below 90%. Rerunning is safe because ingestion is incremental and the queue is merged, not replaced."
- **Be honest:** "What I haven't built yet: a quarantine table for bad rows, a 'today's file never arrived' completeness alert, and job failure notifications. Those are pilot items: a missing-file check per day, a quarantine table, and email or Slack alerts on failure."
**Evidence:** the pipeline event log, `incremental_run.md`, `triggered_run.md`. **Limit:** only the failure cases tested, which are re-delivery and invalid values.

### "Security, integration, operations?"
**Answer:**
- **Security (Unity Catalog):**
  - PII columns are tagged and masked by a function, unless the reader is in a PII-reader group.
  - Gold tables, Genie and the app never see names, emails, phones or VINs.
  - The app's service principal can read only the gold tables.
  - Genie runs *on behalf of the signed-in user*, so their own permissions apply.
- **Rules inside the app:** input validation on every case update (allowed statuses, case-ID format). The user's identity comes from the platform, not from a form field.
- **Integration:** "Your export lands as files in a Unity Catalog volume, the same as your vendor export today, so nothing changes at the source. The queue is in Postgres, so your case system can read it directly."
- **Operations:**
  - Two code bundles in Git (pipeline and job; app) and one job with a file-arrival trigger.
  - The data-quality and consistency checks fail the job.
  - Alert notifications to your on-call channel are a pilot step.
**Evidence:** the governance evidence (masked sample, column tags) and the app's resource and scope snapshot. **Limit:** "In our test, only two identities: my user and the app's service principal. I haven't yet tested a second, non-PII user end to end."

### Other likely objections (quick answers)
| From | Objection | Answer |
|---|---|---|
| Business | "Why not just ask the vendor to improve?" | "Their tool can't join your vehicle, dealer and OTA data, and the export is monthly. The detection gap is architectural, not a setting." |
| Business | "How fast can we see value?" | "30 days: replay your last real issue on 3 months of exports. The rules migrate as data from day one." |
| Business | "Is the $4.0M real?" | "It's an estimate. The conservative number is $1.7M; the extra $2.3M rests on defection assumptions we'd validate in the pilot." |
| Technical | "Why not one LLM for everything?" | "Cost, determinism and auditability. Rules give exact explanations, AI handles nuance, and a small trained model does sentiment at no token cost." |
| Technical | "Scale to 240K a month?" | "Serverless and incremental. AI cost grows with *distinct* wording, not volume; the rule engine runs in parallel as a PySpark UDF." |

---

## 3 · Demo route: claim → what's on screen

| Claim | On screen |
|---|---|
| Defect detected 2 days after release | Slide 4 timeline · Overview → emerging issues · Genie "first detected" answer |
| 77.9% → 99.4% of complaints found | Slide 7 · Monitoring → tagging accuracy |
| AI catches paraphrases, rules explain | Topics → a quote marked *AI only* with its reason; one with keywords |
| Every P1 has an owner and an audit trail | **Live:** Escalation queue → save a case |
| The loop is closed | Monitoring → case handling shows the saved case |
| Self-service answers you can check | Ask Genie → open Generated SQL |
| Governed, no PII | Slide 10 masked table |
| Cost stays flat | Slide 10 (4,018 calls for 11,953 sentences; 43 per new day) |

Use slides or the recording for anything slow (job runs, the pipeline UI, Lakebase).

---

## 4 · The close

**Start closing when either happens:** the AI says something like "let's schedule a follow-up" or "this has been helpful", **or** the presenting clock passes **minute 20**.

> "Before we close: we flagged the OTA 4.2 defect **31 days before the month-end report**, and found **99.4% of complaints**. Conservatively that's **$1.7M a year** in cost and risk avoided. The next step is a **30-day pilot on 3 months of your real exports**. Can we agree on **a Quality analyst, a Safety lead and your data platform owner**, and meet **next Tuesday** to pick the pilot dataset? Would Tuesday work?"

Then **pause**, and let them answer.
