import {
  useAnalyticsQuery,
  BarChart,
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

const pct = (v: unknown) => `${(Number(v ?? 0) * 100).toFixed(1)}%`;

function QualityTable() {
  const { data, loading, error } = useAnalyticsQuery('classifier_quality', {});
  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={String(error)} />;
  if (!data || data.length === 0) return <EmptyBlock title="No evaluation yet" description="The evaluate task of the job writes these metrics." />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Method</TableHead>
          <TableHead className="text-right">Precision</TableHead>
          <TableHead className="text-right">Recall</TableHead>
          <TableHead className="text-right">F1</TableHead>
          <TableHead className="text-right">TP / FP / FN</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((r) => (
          <TableRow key={r.method}>
            <TableCell className="font-medium">{r.method}</TableCell>
            <TableCell className="text-right tabular-nums">{pct(r.precision)}</TableCell>
            <TableCell className="text-right tabular-nums">{pct(r.recall)}</TableCell>
            <TableCell className="text-right tabular-nums font-semibold">{pct(r.f1)}</TableCell>
            <TableCell className="text-right tabular-nums">{Number(r.tp)} / {Number(r.fp)} / {Number(r.fn)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function QualityPage() {
  return (
    <div className="space-y-6 w-full max-w-5xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Rules for precision, AI for recall: combining both gives the best F1</CardTitle>
          <CardDescription>
            Sentence × topic tags vs. the generator&apos;s ground-truth labels (synthetic data). Rules = deterministic rule engine;
            ai_classify = Databricks AI Function with plain-language topic definitions.
          </CardDescription>
        </CardHeader>
        <CardContent><QualityTable /></CardContent>
      </Card>
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>Where each topic tag came from</CardTitle>
          <CardDescription>&ldquo;ai&rdquo; = paraphrases the keyword rules missed · source: gold_sentence_topics</CardDescription>
        </CardHeader>
        <CardContent>
          <BarChart queryKey="detection_source" parameters={{}} xKey="detected_by" yKey="tagged_sentences" colorPalette="categorical" height={260} ariaLabel="Tag source" />
        </CardContent>
      </Card>
    </div>
  );
}
