// Escalation-queue routes backed by Lakebase Postgres.
//  * voc_valtera.lb_escalation_queue  -> Lakebase synced table (read-only, refreshed by the pipeline job)
//  * case_mgmt.case_actions           -> app-owned table: status / assignee / note written by agents
import { z } from 'zod';
import type { Application, Request } from 'express';

interface AppKitWithLakebase {
  lakebase: {
    query(text: string, params?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
  };
  server: {
    extend(fn: (app: Application) => void): void;
  };
}

const STATUSES = ['Open', 'Acknowledged', 'In progress', 'Resolved'] as const;

const SETUP_SQL = [
  `CREATE SCHEMA IF NOT EXISTS case_mgmt`,
  `CREATE TABLE IF NOT EXISTS case_mgmt.case_actions (
     case_id    TEXT PRIMARY KEY,
     status     TEXT NOT NULL DEFAULT 'Open',
     assignee   TEXT,
     note       TEXT,
     updated_by TEXT,
     updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   )`,
  `CREATE TABLE IF NOT EXISTS case_mgmt.case_action_log (
     id         BIGSERIAL PRIMARY KEY,
     case_id    TEXT NOT NULL,
     status     TEXT NOT NULL,
     assignee   TEXT,
     note       TEXT,
     updated_by TEXT,
     logged_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
   )`,
  // Lakehouse Sync (Lakebase -> Unity Catalog CDC) needs full row images; only the owner (this app) can set it.
  `ALTER TABLE case_mgmt.case_actions REPLICA IDENTITY FULL`,
  `ALTER TABLE case_mgmt.case_action_log REPLICA IDENTITY FULL`,
];

const LIST_SQL = `
  SELECT q.case_id, q.created_at, q.priority, q.escalation_score, q.primary_topic, q.primary_parent_topic,
         q.topics, q.sentiment, q.nps_score, q.channel, q.model, q.model_year, q.dealer_name, q.dealer_region,
         q.loyalty_tier, q.case_summary, q.recommended_action,
         COALESCE(a.status, 'Open') AS status, a.assignee, a.note, a.updated_by, a.updated_at
  FROM voc_valtera.lb_escalation_queue q
  LEFT JOIN case_mgmt.case_actions a ON a.case_id = q.case_id
  WHERE ($1::text IS NULL OR q.priority = $1)
    AND ($2::text IS NULL OR COALESCE(a.status, 'Open') = $2)
    AND ($3::text IS NULL OR q.primary_parent_topic = $3)
  ORDER BY q.priority, q.escalation_score DESC, q.created_at DESC
  LIMIT 200`;

const SUMMARY_SQL = `
  SELECT q.priority, COALESCE(a.status, 'Open') AS status, COUNT(*)::int AS cases
  FROM voc_valtera.lb_escalation_queue q
  LEFT JOIN case_mgmt.case_actions a ON a.case_id = q.case_id
  GROUP BY 1, 2 ORDER BY 1, 2`;

const UPSERT_SQL = `
  INSERT INTO case_mgmt.case_actions (case_id, status, assignee, note, updated_by, updated_at)
  VALUES ($1, $2, $3, $4, $5, NOW())
  ON CONFLICT (case_id) DO UPDATE SET status = EXCLUDED.status, assignee = EXCLUDED.assignee,
    note = EXCLUDED.note, updated_by = EXCLUDED.updated_by, updated_at = NOW()
  RETURNING *`;

const LOG_SQL = `
  INSERT INTO case_mgmt.case_action_log (case_id, status, assignee, note, updated_by)
  VALUES ($1, $2, $3, $4, $5)`;

const filterSchema = z.object({
  priority: z.enum(['P1', 'P2']).optional(),
  status: z.enum(STATUSES).optional(),
  topic: z.string().max(60).optional(),
});

const updateSchema = z.object({
  status: z.enum(STATUSES),
  assignee: z.string().max(120).optional().nullable(),
  note: z.string().max(2000).optional().nullable(),
});

function currentUser(req: Request): string {
  const email = req.header('x-forwarded-email') ?? req.header('x-forwarded-preferred-username');
  return email ?? 'local-dev';
}

export async function setupCaseRoutes(appkit: AppKitWithLakebase) {
  for (const stmt of SETUP_SQL) {
    await appkit.lakebase.query(stmt);
  }

  appkit.server.extend((app) => {
    app.get('/api/whoami', (req, res) => {
      res.json({ email: req.header('x-forwarded-email') ?? null, user: req.header('x-forwarded-user') ?? null });
    });

    app.get('/api/cases', async (req, res) => {
      const parsed = filterSchema.safeParse(req.query);
      if (!parsed.success) {
        res.status(400).json({ error: 'Invalid filter' });
        return;
      }
      try {
        const { priority, status, topic } = parsed.data;
        const { rows } = await appkit.lakebase.query(LIST_SQL, [priority ?? null, status ?? null, topic ?? null]);
        res.json(rows);
      } catch (err) {
        console.error('list cases failed', err);
        res.status(500).json({ error: 'Could not load the escalation queue' });
      }
    });

    app.get('/api/cases/summary', async (_req, res) => {
      try {
        const { rows } = await appkit.lakebase.query(SUMMARY_SQL);
        res.json(rows);
      } catch (err) {
        console.error('case summary failed', err);
        res.status(500).json({ error: 'Could not load the case summary' });
      }
    });

    app.post('/api/cases/:caseId', async (req, res) => {
      const caseId = String(req.params.caseId ?? '');
      const parsed = updateSchema.safeParse(req.body);
      if (!/^I\d{13}$/.test(caseId) || !parsed.success) {
        res.status(400).json({ error: 'Invalid case update' });
        return;
      }
      try {
        const user = currentUser(req);
        const { status, assignee, note } = parsed.data;
        const params = [caseId, status, assignee ?? null, note ?? null, user];
        const { rows } = await appkit.lakebase.query(UPSERT_SQL, params);
        await appkit.lakebase.query(LOG_SQL, params);
        res.json(rows[0]);
      } catch (err) {
        console.error('update case failed', err);
        res.status(500).json({ error: 'Could not save the case update' });
      }
    });
  });
}
