import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDataset } from '../api/datasets';
import { listExamples } from '../api/examples';
import { startScoring, getScoringStatus } from '../api/scoring';
import { reviewExample } from '../api/review';
import { listBuckets } from '../api/buckets';
import { CheckCircle, XCircle, AlertTriangle, Loader, Play } from 'lucide-react';

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [jobId, setJobId] = useState<string | null>(null);
  const [selectedExample, setSelectedExample] = useState<string | null>(null);

  const { data: dataset } = useQuery({
    queryKey: ['datasets', id],
    queryFn: () => getDataset(id!),
    enabled: !!id,
  });

  const { data: examples, refetch: refetchExamples } = useQuery({
    queryKey: ['examples', { dataset_id: id, page }],
    queryFn: () => listExamples({ dataset_id: id!, page, page_size: 20, sort_by: 'aggregate_score', sort_order: 'asc' }),
    enabled: !!id,
  });

  const { data: buckets } = useQuery({
    queryKey: ['buckets'],
    queryFn: listBuckets,
  });

  // Poll scoring status
  const { data: scoringStatus } = useQuery({
    queryKey: ['scoring', jobId],
    queryFn: () => getScoringStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' ? 2000 : false;
    },
  });

  useEffect(() => {
    if (scoringStatus?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['datasets', id] });
      queryClient.invalidateQueries({ queryKey: ['examples'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    }
  }, [scoringStatus?.status]);

  const scoreMutation = useMutation({
    mutationFn: () => startScoring(id!),
    onSuccess: (data) => setJobId(data.job_id),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ exampleId, action }: { exampleId: string; action: 'approved' | 'rejected' }) =>
      reviewExample(exampleId, action),
    onSuccess: () => {
      refetchExamples();
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (!dataset) return <div className="text-gray-500">Loading...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{dataset.name}</h2>
          <p className="text-gray-500 text-sm">{dataset.filename} - {dataset.total_examples.toLocaleString()} examples</p>
        </div>
        {dataset.status !== 'scored' && (
          <button
            onClick={() => scoreMutation.mutate()}
            disabled={scoreMutation.isPending || scoringStatus?.status === 'running'}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white px-4 py-2 rounded-lg"
          >
            <Play className="w-4 h-4" /> Start Scoring
          </button>
        )}
      </div>

      {/* Scoring progress */}
      {scoringStatus && scoringStatus.status === 'running' && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="flex items-center gap-3 mb-3">
            <Loader className="w-5 h-5 text-orange-500 animate-spin" />
            <span className="text-sm text-gray-300">Scoring in progress: {scoringStatus.current_engine}</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div
              className="bg-orange-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${scoringStatus.progress * 100}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">{Math.round(scoringStatus.progress * 100)}%</p>
        </div>
      )}

      {/* Examples table */}
      {examples && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left p-3 text-gray-400 font-medium">Line</th>
                <th className="text-left p-3 text-gray-400 font-medium">User Content</th>
                <th className="text-left p-3 text-gray-400 font-medium">Bucket</th>
                <th className="text-left p-3 text-gray-400 font-medium">Score</th>
                <th className="text-left p-3 text-gray-400 font-medium">Status</th>
                <th className="text-left p-3 text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {examples.items.map((ex) => (
                <tr key={ex.id} className="border-t border-gray-800 hover:bg-gray-800/30">
                  <td className="p-3 text-gray-500 font-mono text-xs">{ex.line_number}</td>
                  <td className="p-3 max-w-md">
                    <p className="truncate text-gray-300">{ex.user_content.slice(0, 100)}</p>
                  </td>
                  <td className="p-3">
                    {ex.bucket_name && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-300">{ex.bucket_name}</span>
                    )}
                  </td>
                  <td className="p-3">
                    {ex.aggregate_score !== null ? (
                      <ScoreBadge score={ex.aggregate_score} />
                    ) : (
                      <span className="text-gray-600">-</span>
                    )}
                  </td>
                  <td className="p-3">
                    <ReviewBadge status={ex.review_status} />
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => reviewMutation.mutate({ exampleId: ex.id, action: 'approved' })}
                        className="p-1 text-gray-500 hover:text-green-400 transition-colors"
                        title="Approve"
                      >
                        <CheckCircle className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => reviewMutation.mutate({ exampleId: ex.id, action: 'rejected' })}
                        className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                        title="Reject"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          <div className="flex items-center justify-between p-3 border-t border-gray-800 text-sm text-gray-500">
            <span>Showing {(page - 1) * examples.page_size + 1}-{Math.min(page * examples.page_size, examples.total)} of {examples.total}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded bg-gray-800 disabled:opacity-50 hover:bg-gray-700"
              >
                Prev
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page * examples.page_size >= examples.total}
                className="px-3 py-1 rounded bg-gray-800 disabled:opacity-50 hover:bg-gray-700"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 0.7 ? 'text-green-400' : score >= 0.4 ? 'text-yellow-400' : 'text-red-400';
  return <span className={`font-mono text-xs ${color}`}>{score.toFixed(2)}</span>;
}

function ReviewBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-gray-700 text-gray-400',
    approved: 'bg-green-500/20 text-green-400',
    rejected: 'bg-red-500/20 text-red-400',
    needs_edit: 'bg-yellow-500/20 text-yellow-400',
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs ${styles[status]}`}>{status}</span>;
}
