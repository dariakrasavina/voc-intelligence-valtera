# valtera-voc-app (Databricks App, AppKit)

Case-management and insight app for the Valtera Motors VOC Intelligence build. See the repo root README.

* **Overview**: KPIs, emerging-issue alerts, Aurora EV trend, top topics, dealer hotspots (SQL warehouse, `config/queries/*.sql`).
* **Escalation queue**: P1/P2 cases read from the Lakebase synced table `voc_valtera.lb_escalation_queue`; status, assignee and
  notes are written to the app-owned Lakebase schema `case_mgmt` (`case_actions` + `case_action_log`). Routes: `server/routes/cases/case-routes.ts`.
* **Ask Genie**: `useGenieChat` against the "Valtera VOC Insights" Genie Agent, with generated SQL, result chart and a disclaimer.
* **Model quality**: rules vs. ai_classify vs. combined, scored against ground truth.

Deploy: `databricks bundle deploy && databricks bundle run app` from this folder (profile with access to the workspace).

**Local build note:** the bundler (tsdown/rolldown) rejects project paths that contain a comma (for example a folder
named `FE-Bar, FY2027`). Deploying is unaffected because Databricks builds the app remotely; for a local
`npm run build` / `databricks apps validate`, use a checkout path without a comma.
