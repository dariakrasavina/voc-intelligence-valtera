# 1. Saved in the app -> Lakebase Postgres case_mgmt.case_actions (latest state) and case_action_log (audit)
    case_id     |    status    |         assignee          |                   note                    |           updated_by           |          updated_at           
----------------+--------------+---------------------------+-------------------------------------------+--------------------------------+-------------------------------
 I2026110700040 | In progress  | Safety investigation team | working on it                             | <redacted> | 2026-11-20 20:04:10.159991+00
 I2026111900007 | Acknowledged | Safety investigation team | please take priority of this request ASAP | <redacted> | 2026-11-20 20:03:52.588954+00
 I2026111700064 | Acknowledged | [name removed]           |                                           | <redacted> | 2026-11-20 18:11:17.957557+00
(3 rows)

 id |    case_id     |    status    |         assignee          |           updated_by           |           logged_at           
----+----------------+--------------+---------------------------+--------------------------------+-------------------------------
  1 | I2026111700064 | Acknowledged | [name removed]           | <redacted> | 2026-11-20 18:11:18.04321+00
  2 | I2026111900007 | Acknowledged | Safety investigation team | <redacted> | 2026-11-20 20:03:52.597713+00
  3 | I2026110700040 | In progress  | Safety investigation team | <redacted> | 2026-11-20 20:04:10.164083+00
(3 rows)


# 2. Lakehouse Sync (CDC) -> Unity Catalog daria_krasavina.voc_valtera.lb_case_actions_history
[
  {
    "_pg_change_type": "insert",
    "assignee": "[name removed]",
    "case_id": "I2026111700064",
    "status": "Acknowledged",
    "synced_at": "2026-11-20 18:30:52.325821"
  },
  {
    "_pg_change_type": "insert",
    "assignee": "Safety investigation team",
    "case_id": "I2026111900007",
    "status": "Acknowledged",
    "synced_at": "2026-11-20 20:03:54.332734"
  },
  {
    "_pg_change_type": "insert",
    "assignee": "Safety investigation team",
    "case_id": "I2026110700040",
    "status": "In progress",
    "synced_at": "2026-11-20 20:04:10.162062"
  }
]

# 3. gold_case_status (what Monitoring and Genie read)
[
  {
    "assignee": "Safety investigation team",
    "case_id": "I2026111900007",
    "last_updated_at": "2026-11-20 15:03:52.588954",
    "note": "please take priority of this request ASAP",
    "primary_topic": "Safety - Unexpected Braking",
    "priority": "P1",
    "status": "Acknowledged"
  },
  {
    "assignee": "Safety investigation team",
    "case_id": "I2026110700040",
    "last_updated_at": "2026-11-20 15:04:10.159991",
    "note": "working on it",
    "primary_topic": "Safety - Unexpected Braking",
    "priority": "P1",
    "status": "In progress"
  }
]
