import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
} from '@databricks/appkit-ui/react';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/States';

const STATUSES = ['Open', 'Acknowledged', 'In progress', 'Resolved'] as const;
type Status = (typeof STATUSES)[number];
const ALL = 'all';

interface CaseRow {
  case_id: string;
  created_at: string;
  priority: string;
  escalation_score: number | string;
  primary_topic: string;
  primary_parent_topic: string;
  topics: string;
  sentiment: string;
  nps_score: number | null;
  channel: string;
  model: string;
  model_year: number;
  dealer_name: string;
  dealer_region: string;
  loyalty_tier: string;
  case_summary: string;
  recommended_action: string;
  status: Status;
  assignee: string | null;
  note: string | null;
  updated_by: string | null;
  updated_at: string | null;
}

function isCaseRows(v: unknown): v is CaseRow[] {
  return Array.isArray(v) && v.every((r) => typeof r === 'object' && r !== null && 'case_id' in r);
}

function CaseEditor({ row, onSaved }: { row: CaseRow; onSaved: () => void }) {
  const [status, setStatus] = useState<Status>(row.status);
  const [assignee, setAssignee] = useState(row.assignee ?? '');
  const [note, setNote] = useState(row.note ?? '');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setErr(null);
    try {
      const r = await fetch(`/api/cases/${row.case_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, assignee: assignee || null, note: note || null }),
      });
      if (!r.ok) throw new Error(`Save failed (${r.status})`);
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Badge variant={row.priority === 'P1' ? 'destructive' : 'secondary'}>{row.priority}</Badge>
          {row.primary_topic}
        </CardTitle>
        <CardDescription>
          Case {row.case_id} · {row.channel} · {row.model} {row.model_year} · {row.dealer_name} ({row.dealer_region}) · {row.loyalty_tier} customer
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs font-medium text-muted-foreground">AI case summary (ai_summarize — verify against the transcript)</p>
          <p className="text-sm">{row.case_summary}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Recommended action</p>
          <p className="text-sm">{row.recommended_action}</p>
        </div>
        <p className="text-xs text-muted-foreground">All topics: {row.topics || '—'} · sentiment {row.sentiment} · score {Number(row.escalation_score).toFixed(1)}</p>
        <div className="space-y-2">
          <Label htmlFor="status">Status</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as Status)}>
            <SelectTrigger id="status"><SelectValue /></SelectTrigger>
            <SelectContent>
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="assignee">Assignee</Label>
          <Input id="assignee" value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder="e.g. EV specialist team" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="note">Note</Label>
          <Textarea id="note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What was done, next step" />
        </div>
        {err && <ErrorBlock message={err} />}
        <div className="flex items-center gap-3">
          <Button onClick={() => void save()} disabled={saving}>{saving ? 'Saving…' : 'Save to Lakebase'}</Button>
          {row.updated_at && (
            <span className="text-xs text-muted-foreground">
              Last update {new Date(row.updated_at).toLocaleString()} by {row.updated_by}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function CasesPage() {
  const [rows, setRows] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [priority, setPriority] = useState<string>(ALL);
  const [status, setStatus] = useState<string>(ALL);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const qs = new URLSearchParams();
    if (priority !== ALL) qs.set('priority', priority);
    if (status !== ALL) qs.set('status', status);
    try {
      const r = await fetch(`/api/cases?${qs.toString()}`);
      if (!r.ok) throw new Error(`Request failed (${r.status})`);
      const body: unknown = await r.json();
      setRows(isCaseRows(body) ? body : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    }
  }, [priority, status]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => rows?.find((r) => r.case_id === selectedId) ?? null, [rows, selectedId]);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of rows ?? []) c[r.status] = (c[r.status] ?? 0) + 1;
    return c;
  }, [rows]);

  return (
    <div className="space-y-4 w-full max-w-7xl mx-auto">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <h2 className="text-xl font-semibold">Escalation queue</h2>
          <p className="text-sm text-muted-foreground">
            P1/P2 cases from the last 30 days, served from Lakebase (synced from gold_escalation_queue). Updates are written to Lakebase
            case_mgmt.case_actions with an audit log.
          </p>
        </div>
        <div className="ml-auto flex gap-3">
          <Select value={priority} onValueChange={setPriority}>
            <SelectTrigger className="w-36" aria-label="Priority"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All priorities</SelectItem>
              <SelectItem value="P1">P1</SelectItem>
              <SelectItem value="P2">P2</SelectItem>
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-40" aria-label="Status"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex gap-2 text-sm">
        {STATUSES.map((s) => <Badge key={s} variant="outline">{s}: {counts[s] ?? 0}</Badge>)}
        <span className="text-xs text-muted-foreground self-center">(showing up to 200, highest priority first)</span>
      </div>
      {error && <ErrorBlock message={error} />}
      {!rows && !error && <LoadingBlock rows={6} />}
      {rows && rows.length === 0 && <EmptyBlock title="No cases match" description="Change the priority or status filter." />}
      {rows && rows.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <Card className="lg:col-span-3 min-w-0">
            <CardContent className="pt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Priority</TableHead>
                    <TableHead>Topic</TableHead>
                    <TableHead>Vehicle</TableHead>
                    <TableHead>Received</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow
                      key={r.case_id}
                      onClick={() => setSelectedId(r.case_id)}
                      data-state={r.case_id === selectedId ? 'selected' : undefined}
                      className="cursor-pointer"
                    >
                      <TableCell><Badge variant={r.priority === 'P1' ? 'destructive' : 'secondary'}>{r.priority}</Badge></TableCell>
                      <TableCell>
                        <button type="button" className="text-left hover:underline" onClick={() => setSelectedId(r.case_id)}>
                          {r.primary_topic}
                        </button>
                      </TableCell>
                      <TableCell>{r.model} {r.model_year}</TableCell>
                      <TableCell className="tabular-nums">{new Date(r.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>{r.status}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <div className="lg:col-span-2">
            {selected ? (
              <CaseEditor key={selected.case_id} row={selected} onSaved={() => void load()} />
            ) : (
              <EmptyBlock title="Select a case" description="Pick a case to see the AI summary and update its status." />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
