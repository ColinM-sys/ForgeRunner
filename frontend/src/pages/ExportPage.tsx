import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { listDatasets } from '../api/datasets';
import { listBuckets } from '../api/buckets';
import { createExport } from '../api/export';
import { Download, FileText, CheckCircle } from 'lucide-react';
import type { ExportResponse } from '../types';

export default function ExportPage() {
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);
  const [selectedBuckets, setSelectedBuckets] = useState<string[]>([]);
  const [reviewStatus, setReviewStatus] = useState('approved');
  const [minScore, setMinScore] = useState<string>('');
  const [exportResult, setExportResult] = useState<ExportResponse | null>(null);

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasets,
  });

  const { data: buckets } = useQuery({
    queryKey: ['buckets'],
    queryFn: listBuckets,
  });

  const exportMutation = useMutation({
    mutationFn: () => createExport({
      dataset_ids: selectedDatasets.length > 0 ? selectedDatasets : undefined,
      bucket_ids: selectedBuckets.length > 0 ? selectedBuckets : undefined,
      review_status: reviewStatus || undefined,
      min_score: minScore ? parseFloat(minScore) : undefined,
    }),
    onSuccess: (data) => setExportResult(data),
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Export Data</h2>

      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-5">
        {/* Review status filter */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Review Status</label>
          <select
            value={reviewStatus}
            onChange={(e) => setReviewStatus(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-300"
          >
            <option value="approved">Approved only</option>
            <option value="pending">Pending only</option>
            <option value="rejected">Rejected only</option>
            <option value="">All statuses</option>
          </select>
        </div>

        {/* Datasets filter */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Datasets (leave empty for all)</label>
          <div className="space-y-1 max-h-40 overflow-auto">
            {datasets?.map(ds => (
              <label key={ds.id} className="flex items-center gap-2 text-sm text-gray-300 p-1">
                <input
                  type="checkbox"
                  checked={selectedDatasets.includes(ds.id)}
                  onChange={(e) => {
                    if (e.target.checked) setSelectedDatasets([...selectedDatasets, ds.id]);
                    else setSelectedDatasets(selectedDatasets.filter(id => id !== ds.id));
                  }}
                  className="rounded"
                />
                {ds.name} ({ds.total_examples.toLocaleString()})
              </label>
            ))}
          </div>
        </div>

        {/* Buckets filter */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Buckets (leave empty for all)</label>
          <div className="space-y-1 max-h-40 overflow-auto">
            {buckets?.map(b => (
              <label key={b.id} className="flex items-center gap-2 text-sm text-gray-300 p-1">
                <input
                  type="checkbox"
                  checked={selectedBuckets.includes(b.id)}
                  onChange={(e) => {
                    if (e.target.checked) setSelectedBuckets([...selectedBuckets, b.id]);
                    else setSelectedBuckets(selectedBuckets.filter(id => id !== b.id));
                  }}
                  className="rounded"
                />
                <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: b.color }} />
                {b.display_name} ({b.example_count})
              </label>
            ))}
          </div>
        </div>

        {/* Min score filter */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Minimum Score (0.0 - 1.0)</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="No minimum"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-300"
          />
        </div>

        <button
          onClick={() => exportMutation.mutate()}
          disabled={exportMutation.isPending}
          className="w-full flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white font-medium py-3 rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          {exportMutation.isPending ? 'Exporting...' : 'Export JSONL'}
        </button>
      </div>

      {/* Export result */}
      {exportResult && (
        <div className="bg-gray-900 rounded-xl p-6 border border-green-500/30 space-y-3">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" />
            <h3 className="font-semibold">Export Ready</h3>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <FileText className="w-4 h-4 text-gray-500" />
            <span className="text-gray-300">{exportResult.filename}</span>
            <span className="text-gray-500">({exportResult.total_examples.toLocaleString()} examples)</span>
          </div>
          <a
            href={exportResult.download_url}
            download
            className="inline-flex items-center gap-2 bg-green-500/20 text-green-400 px-4 py-2 rounded-lg hover:bg-green-500/30 text-sm"
          >
            <Download className="w-4 h-4" /> Download
          </a>
        </div>
      )}
    </div>
  );
}
