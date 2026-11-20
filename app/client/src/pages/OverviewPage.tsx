import {
  useAnalyticsQuery,
  BarChart,
  LineChart,
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
  Badge,
} from '@databricks/appkit-ui/react';
import { AlertTriangle } from 'lucide-react';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/States';

const num = (v: unknown) => Number(v ?? 0);

function Kpi({ label, value, unit, note }: { label: string; value: string; unit?: string; note: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">
          {value}
          {unit && <span className="text-base font-normal text-muted-foreground ml-1">{unit}</span>}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{note}</CardContent>
    </Card>
  );
}

function KpiRow() {
  const { data, loading, error } = useAnalyticsQuery('kpis', {});
  if (loading) return <LoadingBlock rows={2} />;
  if (error) return <ErrorBlock message={String(error)} />;
  const k = data?.[0];
  if (!k) return <EmptyBlock title="No interactions yet" description="Run the valtera-voc-end-to-end job to load data." />;
  const period = `Last 30 days to ${k.as_of_date}`;
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
      <Kpi label="Customer interactions" value={num(k.interactions).toLocaleString()} note={`${period} · calls + surveys`} />
      <Kpi label="Negative sentiment" value={num(k.negative_pct).toFixed(1)} unit="%" note="share of interactions · sentiment model" />
      <Kpi label="Positive sentiment" value={num(k.positive_pct).toFixed(1)} unit="%" note="share of interactions · sentiment model" />
      <Kpi label="Average survey NPS score" value={num(k.avg_nps).toFixed(1)} unit="/ 10" note="post-service surveys only" />
      <Kpi label="Safety-related interactions" value={num(k.safety_interactions).toLocaleString()} note="Vehicle Safety topics" />
      <Kpi label="P1 cases" value={num(k.p1_cases).toLocaleString()} note="safety or high escalation score" />
    </div>
  );
}

function EmergingIssues() {
  const { data, loading, error } = useAnalyticsQuery('emerging_issues', {});
  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0)
    return <EmptyBlock title="No emerging issues" description="No topic × vehicle is above 3× its 4-week baseline." />;
  const top = data[0];
  return (
    <Card className="border-destructive">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-5 w-5" aria-hidden />
          {data.length} emerging issue{data.length > 1 ? 's' : ''}: {top.topic_name} on {top.model} {top.model_year} peaked at{' '}
          {num(top.peak_lift).toFixed(1)}× its baseline
        </CardTitle>
        <CardDescription>
          Rule evaluated daily: ≥10 interactions in 7 days and ≥4× the weekly average of the prior 4 weeks. Data as of {top.as_of_date}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Topic</TableHead>
              <TableHead>Vehicle</TableHead>
              <TableHead>First alert</TableHead>
              <TableHead className="text-right">Peak lift</TableHead>
              <TableHead className="text-right">Last 7 days</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((r) => (
              <TableRow key={`${r.topic_name}-${r.model}-${r.model_year}`}>
                <TableCell>
                  {r.topic_name}{' '}
                  {r.parent_topic === 'Vehicle Safety' && <Badge variant="destructive">Safety</Badge>}
                </TableCell>
                <TableCell>{r.model} {r.model_year}</TableCell>
                <TableCell className="tabular-nums">{r.first_alert_date}</TableCell>
                <TableCell className="text-right tabular-nums font-semibold">{num(r.peak_lift).toFixed(1)}×</TableCell>
                <TableCell className="text-right tabular-nums">{num(r.last_7d)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function DealerHotspots() {
  const { data, loading, error } = useAnalyticsQuery('dealer_hotspots', {});
  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0) return <EmptyBlock title="No dealer data" description="No dealer has 50+ interactions yet." />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Dealer</TableHead>
          <TableHead>Region</TableHead>
          <TableHead className="text-right">Interactions</TableHead>
          <TableHead className="text-right">Negative %</TableHead>
          <TableHead className="text-right">Poor-experience complaints</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((r) => (
          <TableRow key={r.dealer_name}>
            <TableCell>{r.dealer_name}</TableCell>
            <TableCell>{r.dealer_region}</TableCell>
            <TableCell className="text-right tabular-nums">{num(r.interactions)}</TableCell>
            <TableCell className="text-right tabular-nums">{num(r.negative_pct).toFixed(1)}</TableCell>
            <TableCell className="text-right tabular-nums">{num(r.poor_experience)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function OverviewPage() {
  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <KpiRow />
      <EmergingIssues />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>What customers talk about most</CardTitle>
            <CardDescription>Top 10 complaint topics by interactions in the last 30 days, and how many of those were negative · praise excluded</CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart queryKey="top_topics" parameters={{}} xKey="topic_name" yKey={['interactions', 'negative_interactions']}
              orientation="horizontal" colorPalette="categorical" height={340} ariaLabel="Top complaint topics" />
          </CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>How customers feel, week by week</CardTitle>
            <CardDescription>Interactions per week by sentiment (trained sentiment model) · all calls and surveys</CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart queryKey="sentiment_weekly" parameters={{}} xKey="week" yKey={['negative', 'neutral', 'positive']}
              stacked colorPalette="categorical" height={340} ariaLabel="Weekly interactions by sentiment" />
          </CardContent>
        </Card>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>2026 Aurora EV: charge-port and braking complaints jumped after OTA 4.2</CardTitle>
            <CardDescription>Mentions per week by topic · OTA 4.2 shipped 2026-10-28 · source: gold_topic_daily</CardDescription>
          </CardHeader>
          <CardContent>
            <LineChart queryKey="aurora_trend" parameters={{}} xKey="week"
              yKey={['charge_port_door', 'unexpected_braking', 'ota_update_failure']}
              colorPalette="categorical" showSymbol height={320} ariaLabel="Weekly 2026 Aurora EV complaints by topic" />
          </CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>Survey feedback by vehicle: promoters vs. detractors</CardTitle>
            <CardDescription>Post-service survey responses · promoters 9-10, passives 7-8, detractors 0-6</CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart queryKey="nps_breakdown" parameters={{}} xKey="model" yKey={['promoters', 'passives', 'detractors']}
              stacked colorPalette="categorical" height={320} ariaLabel="NPS breakdown by model" />
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Dealer hotspots</CardTitle>
          <CardDescription>All-time, dealers with ≥50 interactions, sorted by poor-experience complaints · source: gold_interaction_insights</CardDescription>
        </CardHeader>
        <CardContent>
          <DealerHotspots />
        </CardContent>
      </Card>
    </div>
  );
}
