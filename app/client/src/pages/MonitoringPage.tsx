import {
  useAnalyticsQuery,
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@databricks/appkit-ui/react';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/States';

const num = (v: unknown) => Number(v ?? 0);
const pct = (v: unknown) => `${(num(v) * 100).toFixed(1)}%`;

function Freshness() {
  const { data, loading, error } = useAnalyticsQuery('freshness', {});
  if (loading) return <LoadingBlock rows={2} />;
  if (error) return <ErrorBlock message={String(error)} />;
  const f = data?.[0];
  if (!f) return <EmptyBlock title="No data yet" description="Land an export to start the pipeline." />;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
      <div><p className="text-muted-foreground text-xs">Newest interaction</p><p className="text-lg font-semibold">{f.latest_interaction_date}</p></div>
      <div><p className="text-muted-foreground text-xs">Insights last rebuilt</p><p className="text-lg font-semibold">{String(f.gold_refreshed_at).slice(0, 16).replace('T', ' ')} UTC</p></div>
      <div><p className="text-muted-foreground text-xs">Interactions processed</p><p className="text-lg font-semibold">{num(f.total_interactions).toLocaleString()}</p></div>
      <div><p className="text-muted-foreground text-xs">Days of data</p><p className="text-lg font-semibold">{num(f.days_of_data)}</p></div>
    </div>
  );
}

function AlertHistory() {
  const { data, loading, error } = useAnalyticsQuery('alert_history', {});
  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0) return <EmptyBlock title="No alerts so far" description="The rule has not fired for any topic and vehicle." />;
  return (
    <Table>
      <TableHeader><TableRow>
        <TableHead>First alert</TableHead><TableHead>Topic</TableHead><TableHead>Vehicle</TableHead>
        <TableHead className="text-right">Peak lift</TableHead><TableHead>Status</TableHead>
      </TableRow></TableHeader>
      <TableBody>
        {data.map((r) => (
          <TableRow key={`${r.topic_name}-${r.model}-${r.model_year}`}>
            <TableCell className="tabular-nums">{r.first_alert_date}</TableCell>
            <TableCell>{r.topic_name}</TableCell>
            <TableCell>{r.model} {r.model_year}</TableCell>
            <TableCell className="text-right tabular-nums">{num(r.peak_lift).toFixed(1)}×</TableCell>
            <TableCell><Badge variant={String(r.is_alert) === 'true' ? 'destructive' : 'outline'}>{String(r.is_alert) === 'true' ? 'active' : 'past'}</Badge></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function CaseHandling() {
  const { data, loading, error } = useAnalyticsQuery('case_handling', {});
  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0) return <EmptyBlock title="No cases" description="No P1/P2 cases in the last 30 days." />;
  return (
    <Table>
      <TableHeader><TableRow>
        <TableHead>Priority</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Cases</TableHead>
        <TableHead className="text-right">Avg hours to first action</TableHead>
      </TableRow></TableHeader>
      <TableBody>
        {data.map((r) => (
          <TableRow key={`${r.priority}-${r.status}`}>
            <TableCell><Badge variant={r.priority === 'P1' ? 'destructive' : 'secondary'}>{r.priority}</Badge></TableCell>
            <TableCell>{r.status}</TableCell>
            <TableCell className="text-right tabular-nums">{num(r.cases).toLocaleString()}</TableCell>
            <TableCell className="text-right tabular-nums">{r.avg_hours_to_first_action == null ? '—' : num(r.avg_hours_to_first_action).toFixed(1)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function Accuracy() {
  const { data, loading, error } = useAnalyticsQuery('classifier_quality', {});
  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0) return <EmptyBlock title="No evaluation yet" description="The job's evaluate task writes these metrics." />;
  return (
    <Table>
      <TableHeader><TableRow>
        <TableHead>Method</TableHead><TableHead className="text-right">Precision</TableHead>
        <TableHead className="text-right">Recall</TableHead><TableHead className="text-right">F1</TableHead>
      </TableRow></TableHeader>
      <TableBody>
        {data.map((r) => (
          <TableRow key={r.method}>
            <TableCell className="font-medium">{r.method}</TableCell>
            <TableCell className="text-right tabular-nums">{pct(r.precision)}</TableCell>
            <TableCell className="text-right tabular-nums">{pct(r.recall)}</TableCell>
            <TableCell className="text-right tabular-nums font-semibold">{pct(r.f1)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function MonitoringPage() {
  return (
    <div className="space-y-6 w-full max-w-6xl mx-auto">
      <div>
        <h2 className="text-xl font-semibold">How customer feedback is monitored</h2>
        <p className="text-sm text-muted-foreground">
          Every new contact-center or survey export starts the pipeline automatically (file-arrival trigger): ingest with Auto Loader,
          tag topics with rules + AI, score sentiment, check for emerging issues, and refresh the escalation queue.
        </p>
      </div>
      <Card><CardHeader><CardTitle>Data freshness</CardTitle><CardDescription>source: gold_interaction_insights</CardDescription></CardHeader>
        <CardContent><Freshness /></CardContent></Card>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>How emerging issues are detected</CardTitle>
            <CardDescription>
              Checked every day for each topic × model × model year: alert when there are at least 10 interactions in 7 days and at
              least 4× the weekly average of the previous 4 weeks. Alerts go to an analyst for review.
            </CardDescription>
          </CardHeader>
          <CardContent><AlertHistory /></CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>How escalation cases are handled</CardTitle>
            <CardDescription>
              Status, assignee and notes saved in the Escalation queue (Lakebase) stream back to the lakehouse via Lakehouse Sync ·
              source: gold_case_status
            </CardDescription>
          </CardHeader>
          <CardContent><CaseHandling /></CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>How accurate the topic tagging is</CardTitle>
          <CardDescription>
            Checked on every run against labelled data (synthetic). Rules give explainable precision; AI catches paraphrases; together
            they find nearly every complaint.
          </CardDescription>
        </CardHeader>
        <CardContent><Accuracy /></CardContent>
      </Card>
    </div>
  );
}
