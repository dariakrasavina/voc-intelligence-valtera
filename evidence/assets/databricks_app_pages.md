# Databricks App pages (app/client/src)

| Route | Page | Data used |
|---|---|---|
| `/` | OverviewPage | SQL: aurora_trend, SQL: dealer_hotspots, SQL: emerging_issues, SQL: kpis, SQL: nps_breakdown, SQL: sentiment_weekly, SQL: top_topics |
| `/cases` | CasesPage | Lakebase via /api/cases (read queue, write case actions) |
| `/topics` | TopicsPage | SQL: detection_by_group, SQL: topic_group_sentiment, SQL: topic_group_share, SQL: topic_group_weekly, SQL: topic_overview, SQL: topic_quotes |
| `/monitoring` | MonitoringPage | SQL: alert_history, SQL: case_handling, SQL: classifier_quality, SQL: freshness |
| `/ask` | AskPage | Genie Agent via useGenieChat (alias voc) |

## Deployed app resources

- sql-warehouse: {"sql_warehouse": {"id": "148ccb90800933a1", "permission": "CAN_USE"}}
- genie-space: {"genie_space": {"name": "Valtera VOC Insights", "permission": "CAN_RUN", "space_id": "01f1e46e16d61008a7f72226f0aacb03"}}
- postgres: {"postgres": {"branch": "projects/valtera-voc/branches/production", "database": "projects/valtera-voc/branches/production/databases/databricks-postgres", "permission": "CAN_CONNECT_AND_CREATE"}}

user_api_scopes: ['genie'] (Genie runs on behalf of the signed-in user)
