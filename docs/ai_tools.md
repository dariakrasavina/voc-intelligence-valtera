# AI tools used to build Valtera VOC Intelligence

Two kinds of AI are involved: **AI tools I used to build the solution**, and **AI that runs inside the solution**.
Everything below is what was actually used for this build (2026-11-19/20), not a wish list.

## 1. AI tools I used to build it

### Coding agent
| Tool | How I used it |
|---|---|
| **Claude Code** (Databricks Isaac, Claude Opus) | Pair programmer for the whole build: synthetic data generator, Lakeflow pipeline SQL, job notebooks, porting my earlier rule-engine and ai_classify code, the AppKit app, tests, evidence scripts, README and deck. Debugging included the serverless UDF pickling error, the emerging-issue baseline bug, the Lakebase change-feed break and the file-arrival trigger loop. Every decision and change was reviewed and directed by me. |

### Databricks agent skills (`databricks aitools`, from github.com/databricks/databricks-agent-skills)
The Databricks skills plugin for Claude Code (v0.2.28 during the build, updated to v0.2.30 with `databricks aitools install`).
Skills give the agent current, Databricks-approved guidance for each product, instead of relying on its training data.

| Skill | Used for |
|---|---|
| `databricks-core` | CLI usage, profile/auth handling, data exploration commands |
| `databricks-pipelines` | Lakeflow Declarative Pipeline in SQL: Auto Loader (`STREAM read_files`), AUTO CDC (SCD1), expectations, materialized views |
| `databricks-jobs` | Serverless multi-task job, file-arrival trigger syntax, the one-of schedule/trigger/continuous rule |
| `databricks-lakebase` | Lakebase Autoscaling project, synced table (`create-synced-table`), service-principal grants |
| `databricks-apps` | AppKit scaffolding (`databricks apps init`), analytics + Lakebase + Genie plugins, typegen, `apps validate` |
| `databricks-app-design` | Data-screen design and the Genie trust patterns: generated SQL shown, live status, per-answer disclaimer, honest execution-identity note |
| `databricks-ai-functions` | Reviewed the ai_classify usage. Note: the skill documents ai_classify up to version 2.0; this build uses v2.1 (confidence scores + rationales), which the workspace accepts (350 calls, 0 errors) |
| `databricks-dabs` | Reviewed both bundles; both pass `databricks bundle validate --strict` |

### Databricks developer tooling with AI features
| Tool | Used for |
|---|---|
| **Databricks AppKit** (`@databricks/appkit`, `@databricks/appkit-ui`) | The app framework: `useAnalyticsQuery`, charts, `useGenieChat`, `GenieQueryVisualization`, `lakebase()` plugin, `appkit generate-types`, built-in agent docs (`npx @databricks/appkit docs`) |
| **Databricks CLI** `experimental aitools tools` | Running and checking SQL from the agent (`query`, `get-default-warehouse`), for every data check, grant and evidence query |
| **Genie benchmark evaluation** (`databricks genie genie-create-eval-run`, Beta) | Scored the Genie Agent against 6 benchmark questions: 3/6 → 5/6 after fixing its instructions |

### Other assistants
| Tool | Used for |
|---|---|
| **Glean** (via MCP) | Finding the FE Bar FAQ and the Skills Navigator Jira epic |

## 2. AI inside the solution

| Capability | Where | Why this one |
|---|---|---|
| `ai_classify` v2.1 (multi-label, confidence, rationale) | `03_ai_classify` → `ai_classify_job.py` | Topic tagging from plain-language definitions in `category_model.json`; catches paraphrases the rules miss (100% of them in the test set) |
| `ai_analyze_sentiment` | `04_sentiment_model` | Weak labels, once, to train a small sentiment model (no per-call cost afterwards) |
| Trained sentiment model (scikit-learn, MLflow, UC `@champion`) | `04_sentiment_model` | Owned, versioned, zero-token scoring at volume |
| `ai_summarize` | `05_gold_and_alerts` | One-line case summaries for P1/P2 cases (cached per case) |
| **Genie Agent** "Valtera VOC Insights" | `src/genie/genie_space.py`, app "Ask Genie" tab | Natural-language questions over the gold tables and metric view, with generated SQL shown |

## 3. How the AI output is checked

- Every run scores the rule engine, ai_classify and their combination against ground-truth labels (`07_evaluate`).
- ai_classify keeps the full, ungated response (confidence + rationale) for audit; results are cached by
  (sentence, definitions fingerprint), so edited definitions are always re-classified (`tests/test_ai_common.py`).
- The Genie Agent has version-controlled benchmarks; every Genie answer in the app shows its SQL and a disclaimer.
- AI case summaries are labelled "verify against the transcript" in the app.

## 4. My own prior work reused

The classification code is ported from an earlier VOC project of mine (rule engine, the PySpark `pandas_udf` tagging
job, and the ai_classify v2.1 track). Only code was reused; the Valtera taxonomy, rules, definitions and data are new.
