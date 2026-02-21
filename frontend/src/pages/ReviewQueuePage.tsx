import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listExamples } from '../api/examples';
import { reviewExample, batchReview } from '../api/review';
import { listBuckets } from '../api/buckets';
import { CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';

export default function ReviewQueuePage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filterBucket, setFilterBucket] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const { data: examples, refetch } = useQuery({
    queryKey: ['examples', 'review', { page, bucket_id: filterBucket }],
    queryFn: () => listExamples({
      review_status: 'pending',
      bucket_id: filterBucket || undefined,
      page,
      page_size: 20,
      sort_by: 'aggregate_score',
      sort_order: 'asc',
    }),
  });

  const { data: buckets } = useQuery({
    queryKey: ['buckets'],
    queryFn: listBuckets,
  });

  const reviewMutation = useMutation({
    mutationFn: ({ exampleId, action }: { exampleId: string; action: 'approved' | 'rejected' }) =>
      reviewExample(exampleId, action),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const batchMutation = useMutation({
    mutationFn: ({ action }: { action: 'approved' | 'rejected' }) =>
      batchReview(Array.from(selected), action),
    onSuccess: () => {
      setSelected(new Set());
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (!examples) return;
    if (selected.size === examples.items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(examples.items.map(ex => ex.id)));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Review Queue</h2>
        <div className="flex items-center gap-3">
          <select
            value={filterBucket}
            onChange={(e) => { setFilterBucket(e.target.value); setPage(1); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          >
            <option value="">All Buckets</option>
            {buckets?.map(b => (
              <option key={b.id} value={b.id}>{b.display_name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg p-3">
          <span className="text-sm text-gray-400">{selected.size} selected</span>
          <button
            onClick={() => batchMutation.mutate({ action: 'approved' })}
            disabled={batchMutation.isPending}
            className="flex items-center gap-1 bg-green-500/20 text-green-400 px-3 py-1.5 rounded-lg text-sm hover:bg-green-500/30"
          >
            <CheckCircle className="w-4 h-4" /> Approve All
          </button>
          <button
            onClick={() => batchMutation.mutate({ action: 'rejected' })}
            disabled={batchMutation.isPending}
            className="flex items-center gap-1 bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-sm hover:bg-red-500/30"
          >
            <XCircle className="w-4 h-4" /> Reject All
          </button>
        </div>
      )}

      {/* Examples */}
      {examples && examples.items.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-3">
            <input
              type="checkbox"
              checked={selected.size === examples.items.length && examples.items.length > 0}
              onChange={selectAll}
              className="rounded"
            />
            <span className="text-xs text-gray-500">Select all on this page</span>
          </div>

          {examples.items.map((ex) => (
            <div key={ex.id} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <div className="flex items-center gap-3 p-4">
                <input
                  type="checkbox"
                  checked={selected.has(ex.id)}
                  onChange={() => toggleSelect(ex.id)}
                  className="rounded"
                />
                <button
                  onClick={() => setExpandedId(expandedId === ex.id ? null : ex.id)}
                  className="flex-1 text-left"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-300 truncate max-w-xl">{ex.user_content.slice(0, 120)}</p>
                    <div className="flex items-center gap-3">
                      {ex.bucket_name && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-400">{ex.bucket_name}</span>
                      )}
                      {ex.aggregate_score !== null && (
                        <span className={`font-mono text-xs ${ex.aggregate_score >= 0.7 ? 'text-green-400' : ex.aggregate_score >= 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {ex.aggregate_score.toFixed(2)}
                        </span>
                      )}
                      {expandedId === ex.id ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                    </div>
                  </div>
                </button>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => reviewMutation.mutate({ exampleId: ex.id, action: 'approved' })}
                    className="p-2 text-gray-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
                  >
                    <CheckCircle className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => reviewMutation.mutate({ exampleId: ex.id, action: 'rejected' })}
                    className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  >
                    <XCircle className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Expanded view */}
              {expandedId === ex.id && (
                <div className="border-t border-gray-800 p-4 space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">System Prompt</p>
                    <p className="text-sm text-gray-400 bg-gray-800/50 rounded p-2">{ex.system_prompt.slice(0, 200)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">User</p>
                    <p className="text-sm text-gray-300 bg-gray-800/50 rounded p-2 whitespace-pre-wrap">{ex.user_content}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Assistant</p>
                    <p className="text-sm text-gray-300 bg-gray-800/50 rounded p-2 whitespace-pre-wrap max-h-60 overflow-auto">{ex.assistant_content}</p>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-gray-500 pt-2">
            <span>{examples.total} pending examples</span>
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
                disabled={page * 20 >= examples.total}
                className="px-3 py-1 rounded bg-gray-800 disabled:opacity-50 hover:bg-gray-700"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-16 text-gray-500">
          <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500/30" />
          <p>No pending examples to review</p>
        </div>
      )}
    </div>
  );
}
