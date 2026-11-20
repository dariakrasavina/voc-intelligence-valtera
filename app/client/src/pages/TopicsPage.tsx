import { useState } from 'react';
import {
  useAnalyticsQuery,
  BarChart,
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
import { sql } from '@databricks/appkit-ui/js';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/States';

const num = (v: unknown) => Number(v ?? 0);

function Quotes({ topic }: { topic: string }) {
  const { data, loading, error } = useAnalyticsQuery('topic_quotes', { topic: sql.string(topic) });
  if (loading) return <LoadingBlock rows={5} />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0) return <EmptyBlock title="No quotes" description="No tagged sentences for this topic yet." />;
  return (
    <ul className="space-y-3">
      {data.map((r) => (
        <li key={`${r.created_at}-${r.sentence_text}`} className="border-l-2 border-border pl-3">
          <p className="text-sm">&ldquo;{r.sentence_text}&rdquo;</p>
          <p className="text-xs text-muted-foreground">
            {r.channel} · {String(r.created_at).slice(0, 10)} · found by{' '}
            <Badge variant="outline">{r.detected_by === 'both' ? 'rules + AI' : r.detected_by === 'ai' ? 'AI only' : 'rules only'}</Badge>
            {r.matched_terms ? <> · keywords: {r.matched_terms}</> : null}
            {r.ai_confidence != null ? <> · AI confidence {num(r.ai_confidence).toFixed(2)}</> : null}
          </p>
          {r.ai_rationale && <p className="text-xs text-muted-foreground">AI reason: {r.ai_rationale}</p>}
        </li>
      ))}
    </ul>
  );
}

export function TopicsPage() {
  const { data, loading, error } = useAnalyticsQuery('topic_overview', {});
  const [selected, setSelected] = useState<string | null>(null);
  const topic = selected ?? (data && data.length > 0 ? String(data[0].topic_name) : null);

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-semibold">What customers are telling us, by topic</h2>
        <p className="text-sm text-muted-foreground">
          Every topic found in calls and surveys (all data). Each sentence is tagged by keyword rules and by AI (ai_classify); select a
          topic to read what customers actually said.
        </p>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        <Card className="xl:col-span-3 min-w-0">
          <CardHeader>
            <CardTitle>Topics, most discussed first</CardTitle>
            <CardDescription>Interactions mentioning the topic · % of those that were negative · share found only by AI</CardDescription>
          </CardHeader>
          <CardContent>
            {loading && <LoadingBlock rows={8} />}
            {error && <ErrorBlock message={String(error)} />}
            {data && data.length === 0 && <EmptyBlock title="No topics yet" description="Run the pipeline job to classify interactions." />}
            {data && data.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Topic</TableHead>
                    <TableHead className="text-right">Interactions</TableHead>
                    <TableHead className="text-right">Negative %</TableHead>
                    <TableHead className="text-right">Found only by AI</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((r) => (
                    <TableRow key={r.topic_name} onClick={() => setSelected(String(r.topic_name))}
                      data-state={r.topic_name === topic ? 'selected' : undefined} className="cursor-pointer">
                      <TableCell>
                        <button type="button" className="text-left hover:underline" onClick={() => setSelected(String(r.topic_name))}>
                          {r.topic_name}
                        </button>
                        <div className="text-xs text-muted-foreground">{r.parent_topic}</div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{num(r.interactions).toLocaleString()}</TableCell>
                      <TableCell className="text-right tabular-nums">{num(r.negative_pct).toFixed(1)}</TableCell>
                      <TableCell className="text-right tabular-nums">{num(r.ai_only_pct).toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <Card className="xl:col-span-2 min-w-0">
          <CardHeader>
            <CardTitle>{topic ? `What customers said: ${topic}` : 'What customers said'}</CardTitle>
            <CardDescription>Latest 25 tagged sentences, with how each was found</CardDescription>
          </CardHeader>
          <CardContent>{topic ? <Quotes topic={topic} /> : <EmptyBlock title="Select a topic" description="Pick a topic on the left." />}</CardContent>
        </Card>
      </div>
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>How each topic group is detected</CardTitle>
          <CardDescription>
            Tagged sentences by method · &ldquo;AI only&rdquo; = paraphrases the keyword rules missed, which is why both methods run
          </CardDescription>
        </CardHeader>
        <CardContent>
          <BarChart queryKey="detection_by_group" parameters={{}} xKey="parent_topic" yKey={['both_methods', 'rules_only', 'ai_only']}
            stacked orientation="horizontal" colorPalette="categorical" height={300} ariaLabel="Detection method by topic group" />
        </CardContent>
      </Card>
    </div>
  );
}
