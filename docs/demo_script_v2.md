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
- [ ] Two clocks: **presenting time** (target 18 min) and **whole session** (hard stop 30 min).

**Never click during the demo:**
- Don't run the job, land a file or trigger a pipeline update; a run takes about 10 minutes.
- Never "Full refresh" the pipeline.
- Don't edit `category_model.json` or Genie instructions live.
- Don't open Lakebase or Catalog admin pages; use the evidence slides instead.
- In the queue, only change the case you prepared. Don't mass-edit.

---

## 1 · Run of show (about 18 min presenting + questions)

| Min | Slide / screen | Say (tell) | Show | Land (tell) |
|---|---|---|---|---|
| 0–2 | Slide 1–2 | "Valtera reads 240K calls and surveys a month, once a month. I'll show you how they now hear a defect in 2 days, not 30." | Executive summary | "Three things: earlier signal, every complaint tagged, every serious case owned." |
| 2–4 | Slide 3–4 | "Here is what breaks today, and a real example from the data: OTA 4.2." | Timeline: first alert Oct 30 (2 days), safety alert Nov 3 (6 days), vendor report Nov 30 | "31 days earlier for the first alert, 27 for the safety alert. That's about 4 weeks of rollout you could have paused." |
| 4–6 | **App · Overview** | "This is the screen your Quality lead opens every morning." | KPIs, the emerging-issues card (4 alerts), the Aurora EV trend | "The alert opens an analyst review; it doesn't escalate on its own. That's why the unplanted 4th alert isn't a problem." |
| 6–8 | **App · Topics** | "What customers actually say, by topic." | Pick *Charging - Charge Port Door Stuck* → quotes; show one *AI only* quote with its reason | "Rules explain every tag, AI catches the paraphrases: 77.9% → 99.4% of complaints found." |
| 8–11 | **App · Escalation queue** (the one live workflow) | "From signal to owner." | Open the P1 case → AI summary → recommended action → set status / assignee / note → **Save to Lakebase** | "One-line summary instead of a transcript, an owner the same day, every change audited." |
| 11–12 | **App · Monitoring** | "And how you know it's working." | Freshness, alert history, **case handling (your update is there)**, tagging accuracy | "The update you just saw is already in the lakehouse, through Lakehouse Sync." |
| 12–14 | **App · Ask Genie** | "Your analysts stop waiting on report requests." | "When was the charge port door problem on the 2026 Aurora EV first detected?" → open the SQL | "Every answer shows its SQL. 19/20 business benchmarks pass, and the job fails below 90%." |
| 14–16 | Slide 5–6, 10 | Architecture in one breath (for the architect) | One governed flow; gap → product → result; governance + cost | "One platform, one copy of the data, deployed from Git." |
| 16–18 | Slide 11–13 | Value and the path to production | $1.7M conservative, $4.0M with revenue protected (estimates); 30/60/90 plan | Move to the close (section 4) |

**Checkpoint:** if you're past **minute 12 and not yet at Genie**, skip slides 5–6 and 10, and go to slide 11 then the close.

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
