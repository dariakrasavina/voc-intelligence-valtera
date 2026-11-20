# valtera-voc-app (Databricks App, AppKit)

Case-management and insight app for the Valtera Motors VOC Intelligence build. See the repo root README.

* **Overview**: KPIs, emerging-issue alerts, top topics, weekly sentiment, NPS promoters vs. detractors, Aurora EV trend, dealer hotspots (SQL warehouse, `config/queries/*.sql`).
* **Topics**: every detected topic with volume, % negative and detection method; customer quotes per topic.
* **Escalation queue**: P1/P2 cases read from the Lakebase synced table `voc_valtera.lb_escalation_queue`; status, assignee and
  notes are written to the app-owned Lakebase schema `case_mgmt` (`case_actions` + `case_action_log`). Routes: `server/routes/cases/case-routes.ts`.
* **Monitoring**: data freshness, alert rule + history, case handling (from `gold_case_status`, via Lakehouse Sync), tagging accuracy.
* **Ask Genie**: `useGenieChat` against the "Valtera VOC Insights" Genie Agent, running on behalf of the signed-in user (`user_api_scopes: [genie]`), with generated SQL, result chart and a disclaimer.

Deploy: `databricks bundle deploy && databricks bundle run app` from this folder (profile with access to the workspace).

**Local build note:** the bundler (tsdown/rolldown) rejects project paths that contain a comma (for example a folder
named `FE-Bar, FY2027`). Deploying is unaffected because Databricks builds the app remotely; for a local
`npm run build` / `databricks apps validate`, use a checkout path without a comma.
