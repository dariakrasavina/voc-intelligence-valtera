import { describe, expect, it } from 'vitest';
import express from 'express';
import { setupCaseRoutes } from './routes/cases/case-routes';

// In-memory stand-in for the Lakebase plugin: records SQL and returns canned rows.
function fakeAppkit() {
  const calls: { text: string; params?: unknown[] }[] = [];
  const app = express();
  app.use(express.json());
  return {
    calls,
    app,
    appkit: {
      lakebase: {
        query: (text: string, params?: unknown[]) => {
          calls.push({ text, params });
          return Promise.resolve({ rows: [{ case_id: params?.[0], status: params?.[1] }] });
        },
      },
      server: { extend: (fn: (a: express.Application) => void) => fn(app) },
    },
  };
}

async function request(app: express.Application, method: 'GET' | 'POST', path: string, body?: unknown) {
  const server = app.listen(0);
  const port = (server.address() as { port: number }).port;
  try {
    const r = await fetch(`http://127.0.0.1:${port}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'x-forwarded-email': 'agent@example.com' },
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: r.status, json: (await r.json()) as Record<string, unknown> };
  } finally {
    server.close();
  }
}

describe('case routes', () => {
  it('creates the app-owned schema on startup', async () => {
    const f = fakeAppkit();
    await setupCaseRoutes(f.appkit);
    expect(f.calls.some((c) => c.text.includes('CREATE SCHEMA IF NOT EXISTS case_mgmt'))).toBe(true);
  });

  it('saves a valid case update with the caller identity and writes the audit log', async () => {
    const f = fakeAppkit();
    await setupCaseRoutes(f.appkit);
    const r = await request(f.app, 'POST', '/api/cases/I2026103100012', { status: 'Acknowledged', assignee: 'Safety team' });
    expect(r.status).toBe(200);
    const writes = f.calls.filter((c) => c.text.includes('INSERT INTO case_mgmt'));
    expect(writes).toHaveLength(2);
    expect(writes[0].params).toEqual(['I2026103100012', 'Acknowledged', 'Safety team', null, 'agent@example.com']);
  });

  it('rejects an invalid status or case id', async () => {
    const f = fakeAppkit();
    await setupCaseRoutes(f.appkit);
    expect((await request(f.app, 'POST', '/api/cases/I2026103100012', { status: 'Closed' })).status).toBe(400);
    expect((await request(f.app, 'POST', '/api/cases/1;DROP', { status: 'Open' })).status).toBe(400);
  });
});
