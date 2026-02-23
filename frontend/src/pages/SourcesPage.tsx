import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  checkSources, analyzeGaps,
  type SourceResult, type SourceCheckResponse,
  type GapSourceResult, type GapAnalysisResponse,
} from '../api/sources';
import { listDatasets } from '../api/datasets';
import {
  Globe, CheckCircle, XCircle, Loader, ExternalLink, FileText, AlertTriangle,
  TrendingUp, TrendingDown, Minus, Sparkles, Database, ChevronDown, ChevronUp,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid,
} from 'recharts';

const SCORE_COLORS: Record<string, string> = {
  length: '#3B82F6',
  readability: '#8B5CF6',
  structure: '#10B981',
  info_density: '#F59E0B',
  entity_richness: '#EF4444',
};

const REC_CONFIG: Record<string, { color: string; bg: string; icon: typeof TrendingUp; label: string }> = {
  high_value: { color: 'text-green-400', bg: 'bg-green-500/10', icon: TrendingUp, label: 'High Value' },
  moderate_value: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', icon: Minus, label: 'Moderate' },
  low_value: { color: 'text-orange-400', bg: 'bg-orange-500/10', icon: TrendingDown, label: 'Low Value' },
  redundant: { color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircle, label: 'Redundant' },
};

type Tab = 'check' | 'gap';

export default function SourcesPage() {
  const [tab, setTab] = useState<Tab>('check');

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold">Source Checker</h2>
        <p className="text-gray-500 text-sm mt-1">
          Check content quality or analyze how new sources would improve your training data.
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 bg-gray-900 rounded-lg p-1 border border-gray-800">
        <button
          onClick={() => setTab('check')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'check'
              ? 'bg-orange-500/20 text-orange-400'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
          }`}
        >
          <Globe className="w-4 h-4" /> Quick Check
        </button>
        <button
          onClick={() => setTab('gap')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'gap'
              ? 'bg-orange-500/20 text-orange-400'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
          }`}
        >
          <Sparkles className="w-4 h-4" /> Gap Analysis
        </button>
      </div>

      {tab === 'check' ? <QuickCheckTab /> : <GapAnalysisTab />}
    </div>
  );
}


// ── Quick Check Tab ──────────────────────────────────────────────

function QuickCheckTab() {
  const [input, setInput] = useState('');
  const [results, setResults] = useState<SourceCheckResponse | null>(null);

  const checkMutation = useMutation({
    mutationFn: (urls: string[]) => checkSources(urls),
    onSuccess: (data) => setResults(data),
  });

  const handleCheck = () => {
    if (!input.trim()) return;
    checkMutation.mutate([input]);
  };

  return (
    <>
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 space-y-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={"Paste URLs here, one per line:\n\nhttps://example.com/article-1\nhttps://example.com/article-2\nhttps://example.com/press-release\n\n...or paste text with links mixed in"}
          className="w-full h-40 bg-gray-800 border border-gray-700 rounded-lg p-3 text-gray-300 text-sm font-mono resize-y placeholder:text-gray-600 focus:outline-none focus:border-orange-500/50"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600">
            {input.trim() ? `${(input.match(/https?:\/\/[^\s]+/g) || []).length} URL(s) detected` : 'No URLs detected'}
          </span>
          <button
            onClick={handleCheck}
            disabled={checkMutation.isPending || !input.trim()}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white px-5 py-2 rounded-lg transition-colors font-medium"
          >
            {checkMutation.isPending ? (
              <><Loader className="w-4 h-4 animate-spin" /> Checking...</>
            ) : (
              <><Globe className="w-4 h-4" /> Check Sources</>
            )}
          </button>
        </div>
      </div>

      {results && (
        <div className="flex items-center gap-6 bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div>
            <p className="text-xs text-gray-500">Checked</p>
            <p className="text-xl font-bold">{results.total_checked}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Avg Quality</p>
            <p className={`text-xl font-bold ${results.avg_score >= 0.7 ? 'text-green-400' : results.avg_score >= 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
              {(results.avg_score * 100).toFixed(0)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Reachable</p>
            <p className="text-xl font-bold text-green-400">
              {results.results.filter(r => r.reachable).length}/{results.total_checked}
            </p>
          </div>
        </div>
      )}

      {results && results.results.map((result, i) => (
        <SourceCard key={i} result={result} index={i} />
      ))}

      {checkMutation.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4 inline mr-2" />
          {(checkMutation.error as Error).message}
        </div>
      )}
    </>
  );
}


// ── Gap Analysis Tab ─────────────────────────────────────────────

function GapAnalysisTab() {
  const [input, setInput] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [results, setResults] = useState<GapAnalysisResponse | null>(null);

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasets,
  });

  const scoredDatasets = (datasets || []).filter(d => d.status === 'scored');

  const gapMutation = useMutation({
    mutationFn: ({ urls, datasetId }: { urls: string[]; datasetId: string }) =>
      analyzeGaps(urls, datasetId),
    onSuccess: (data) => setResults(data),
  });

  const handleAnalyze = () => {
    if (!input.trim() || !selectedDataset) return;
    gapMutation.mutate({ urls: [input], datasetId: selectedDataset });
  };

  const urlCount = input.trim() ? (input.match(/https?:\/\/[^\s]+/g) || []).length : 0;

  return (
    <>
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 space-y-4">
        {/* Dataset selector */}
        <div>
          <label className="text-xs text-gray-500 font-semibold block mb-1.5">
            Compare against dataset
          </label>
          {scoredDatasets.length === 0 ? (
            <div className="text-sm text-gray-500 bg-gray-800 rounded-lg p-3 flex items-center gap-2">
              <Database className="w-4 h-4" />
              No scored datasets available. Upload and score a dataset first.
            </div>
          ) : (
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-orange-500/50"
            >
              <option value="">Select a dataset...</option>
              {scoredDatasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.total_examples.toLocaleString()} examples)
                </option>
              ))}
            </select>
          )}
        </div>

        {/* URL input */}
        <div>
          <label className="text-xs text-gray-500 font-semibold block mb-1.5">
            Source URLs to analyze
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={"Paste URLs to check against your dataset:\n\nhttps://example.com/new-article\nhttps://example.com/press-release\n\nMax 20 URLs per analysis"}
            className="w-full h-36 bg-gray-800 border border-gray-700 rounded-lg p-3 text-gray-300 text-sm font-mono resize-y placeholder:text-gray-600 focus:outline-none focus:border-orange-500/50"
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600">
            {urlCount > 0 ? `${urlCount} URL(s) detected` : 'No URLs detected'}
            {urlCount > 20 && <span className="text-red-400 ml-2">(max 20)</span>}
          </span>
          <button
            onClick={handleAnalyze}
            disabled={gapMutation.isPending || !input.trim() || !selectedDataset || urlCount > 20}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white px-5 py-2 rounded-lg transition-colors font-medium"
          >
            {gapMutation.isPending ? (
              <><Loader className="w-4 h-4 animate-spin" /> Analyzing...</>
            ) : (
              <><Sparkles className="w-4 h-4" /> Analyze Gaps</>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {results && (
        <>
          {/* Dataset context */}
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-200">
                  Compared against: {results.dataset_name}
                </h3>
                <p className="text-xs text-gray-500">
                  {results.dataset_size.toLocaleString()} existing examples
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                {results.results.filter(r => r.recommendation === 'high_value').length > 0 && (
                  <span className="bg-green-500/10 text-green-400 px-2 py-1 rounded-full">
                    {results.results.filter(r => r.recommendation === 'high_value').length} high value
                  </span>
                )}
                {results.results.filter(r => r.recommendation === 'redundant').length > 0 && (
                  <span className="bg-red-500/10 text-red-400 px-2 py-1 rounded-full">
                    {results.results.filter(r => r.recommendation === 'redundant').length} redundant
                  </span>
                )}
              </div>
            </div>

            {/* Bucket breakdown mini-bar */}
            {results.bucket_breakdown.length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">Dataset Coverage</p>
                <div className="flex rounded-lg overflow-hidden h-3">
                  {results.bucket_breakdown.filter(b => b.count > 0).map((b) => (
                    <div
                      key={b.name}
                      className="h-full transition-all"
                      style={{
                        backgroundColor: b.color,
                        width: `${(b.count / results.dataset_size) * 100}%`,
                      }}
                      title={`${b.display_name}: ${b.count} examples (${((b.count / results.dataset_size) * 100).toFixed(1)}%)`}
                    />
                  ))}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
                  {results.bucket_breakdown.filter(b => b.count > 0).map((b) => (
                    <span key={b.name} className="text-[10px] text-gray-500 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: b.color }} />
                      {b.display_name} ({b.count})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Individual gap results */}
          {results.results.map((result, i) => (
            <GapCard key={i} result={result} index={i} />
          ))}
        </>
      )}

      {gapMutation.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4 inline mr-2" />
          {(gapMutation.error as Error).message}
        </div>
      )}
    </>
  );
}


// ── Gap Analysis Card ────────────────────────────────────────────

function GapCard({ result, index }: { result: GapSourceResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const rec = REC_CONFIG[result.recommendation] || REC_CONFIG.low_value;
  const RecIcon = rec.icon;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-800/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3">
          {/* Recommendation badge */}
          <div className={`mt-0.5 p-1.5 rounded-lg ${rec.bg}`}>
            <RecIcon className={`w-4 h-4 ${rec.color}`} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600 font-mono">#{index + 1}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${rec.bg} ${rec.color}`}>
                {rec.label}
              </span>
              {result.closest_bucket && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: result.closest_bucket_color ? `${result.closest_bucket_color}20` : undefined,
                    color: result.closest_bucket_color || '#9CA3AF',
                  }}
                >
                  {result.closest_bucket}
                </span>
              )}
            </div>
            {result.title && (
              <p className="text-sm font-medium text-gray-200 truncate mt-1">{result.title}</p>
            )}
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-300 truncate block mt-0.5"
              onClick={(e) => e.stopPropagation()}
            >
              {result.url} <ExternalLink className="w-3 h-3 inline" />
            </a>
            <p className="text-xs text-gray-500 mt-1">{result.recommendation_reason}</p>
          </div>

          {/* Novelty + Quality scores */}
          {result.reachable && (
            <div className="text-right flex gap-4">
              <div>
                <div className={`text-lg font-bold ${
                  result.novelty_score >= 0.5 ? 'text-green-400' :
                  result.novelty_score >= 0.3 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {(result.novelty_score * 100).toFixed(0)}%
                </div>
                <div className="text-[10px] text-gray-600 uppercase tracking-wider">Novelty</div>
              </div>
              <div>
                <div className={`text-lg font-bold ${
                  result.content_quality >= 0.7 ? 'text-green-400' :
                  result.content_quality >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {(result.content_quality * 100).toFixed(0)}%
                </div>
                <div className="text-[10px] text-gray-600 uppercase tracking-wider">Quality</div>
              </div>
            </div>
          )}

          <div className="ml-1 mt-1">
            {expanded ? <ChevronUp className="w-4 h-4 text-gray-600" /> : <ChevronDown className="w-4 h-4 text-gray-600" />}
          </div>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && result.reachable && (
        <div className="border-t border-gray-800 p-4 space-y-4">
          {/* Novelty gauge */}
          <div>
            <h4 className="text-xs text-gray-500 font-semibold mb-2">Novelty vs Existing Dataset</h4>
            <div className="relative h-4 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded-full transition-all"
                style={{
                  width: `${result.novelty_score * 100}%`,
                  background: result.novelty_score >= 0.5
                    ? 'linear-gradient(90deg, #22C55E, #4ADE80)'
                    : result.novelty_score >= 0.3
                    ? 'linear-gradient(90deg, #EAB308, #FACC15)'
                    : 'linear-gradient(90deg, #EF4444, #F87171)',
                }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-gray-600 mt-1">
              <span>Redundant</span>
              <span>Highly Novel</span>
            </div>
          </div>

          {/* Bucket coverage */}
          {result.closest_bucket && (
            <div className="flex items-center gap-3 bg-gray-800/50 rounded-lg p-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: result.closest_bucket_color || '#6B7280' }}
              />
              <div className="flex-1">
                <p className="text-xs text-gray-300">Best fit: <span className="font-semibold">{result.closest_bucket}</span></p>
                <p className="text-[10px] text-gray-500">
                  {(result.bucket_coverage * 100).toFixed(1)}% of dataset is in this bucket
                </p>
              </div>
              <span className={`text-xs font-mono ${
                result.bucket_coverage < 0.1 ? 'text-green-400' :
                result.bucket_coverage < 0.3 ? 'text-yellow-400' : 'text-gray-500'
              }`}>
                {result.bucket_coverage < 0.1 ? 'Under-represented' :
                 result.bucket_coverage < 0.3 ? 'Moderate' : 'Well-covered'}
              </span>
            </div>
          )}

          {/* Closest existing examples */}
          {result.closest_examples.length > 0 && (
            <div>
              <h4 className="text-xs text-gray-500 font-semibold mb-2">Most Similar Existing Examples</h4>
              <div className="space-y-2">
                {result.closest_examples.map((ex, i) => (
                  <div key={i} className="flex items-start gap-2 bg-gray-800/30 rounded-lg p-2.5">
                    <span className="text-[10px] text-gray-600 font-mono mt-0.5">#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-400 truncate">{ex.preview || '(empty)'}</p>
                      <div className="flex gap-3 mt-1 text-[10px] text-gray-600">
                        <span>{ex.bucket}</span>
                        <span>Score: {(ex.score * 100).toFixed(0)}</span>
                      </div>
                    </div>
                    <span className={`text-xs font-mono ${
                      ex.similarity >= 0.8 ? 'text-red-400' :
                      ex.similarity >= 0.5 ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      {(ex.similarity * 100).toFixed(0)}% sim
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Content preview */}
          {result.content_preview && (
            <div>
              <h4 className="text-xs text-gray-500 font-semibold mb-2 flex items-center gap-1">
                <FileText className="w-3 h-3" /> Content Preview
              </h4>
              <p className="text-xs text-gray-400 bg-gray-800/50 rounded-lg p-3 leading-relaxed max-h-40 overflow-auto">
                {result.content_preview}
              </p>
            </div>
          )}

          <div className="flex gap-4 text-xs text-gray-500">
            <span>{result.word_count.toLocaleString()} words</span>
          </div>
        </div>
      )}

      {/* Unreachable expanded */}
      {expanded && !result.reachable && (
        <div className="border-t border-gray-800 p-4">
          <p className="text-sm text-red-400/80">{result.recommendation_reason}</p>
        </div>
      )}
    </div>
  );
}


// ── Quick Check Source Card (unchanged) ──────────────────────────

function SourceCard({ result, index }: { result: SourceResult; index: number }) {
  const [expanded, setExpanded] = useState(false);

  const chartData = Object.entries(result.scores).map(([key, value]) => ({
    name: key.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
    score: Math.round(value * 100),
    key,
  }));

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-gray-800/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3">
          <div className={`mt-0.5 p-1.5 rounded-lg ${result.reachable ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
            {result.reachable ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <XCircle className="w-4 h-4 text-red-400" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600 font-mono">#{index + 1}</span>
              {result.title && (
                <span className="text-sm font-medium text-gray-200 truncate">{result.title}</span>
              )}
            </div>
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-300 truncate block mt-0.5"
              onClick={(e) => e.stopPropagation()}
            >
              {result.url} <ExternalLink className="w-3 h-3 inline" />
            </a>
            <p className="text-xs text-gray-500 mt-1">{result.details}</p>
          </div>

          <div className="text-right">
            <div className={`text-2xl font-bold ${
              result.overall_score >= 0.7 ? 'text-green-400' :
              result.overall_score >= 0.4 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {result.reachable ? `${(result.overall_score * 100).toFixed(0)}` : '--'}
            </div>
            <div className="text-[10px] text-gray-600 uppercase tracking-wider">/ 100</div>
          </div>
        </div>
      </div>

      {expanded && result.reachable && (
        <div className="border-t border-gray-800 p-4 space-y-4">
          {chartData.length > 0 && (
            <div>
              <h4 className="text-xs text-gray-500 font-semibold mb-2">Quality Breakdown</h4>
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} width={80} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, color: '#E5E7EB', fontSize: 12 }}
                    formatter={(value: number) => [`${value}%`, 'Score']}
                  />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.key} fill={SCORE_COLORS[entry.key] || '#6B7280'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {result.content_preview && (
            <div>
              <h4 className="text-xs text-gray-500 font-semibold mb-2 flex items-center gap-1">
                <FileText className="w-3 h-3" /> Content Preview
              </h4>
              <p className="text-xs text-gray-400 bg-gray-800/50 rounded-lg p-3 leading-relaxed max-h-40 overflow-auto">
                {result.content_preview}
              </p>
            </div>
          )}

          <div className="flex gap-4 text-xs text-gray-500">
            <span>HTTP {result.status_code}</span>
            <span>{result.word_count.toLocaleString()} words</span>
          </div>
        </div>
      )}

      {expanded && !result.reachable && (
        <div className="border-t border-gray-800 p-4">
          <p className="text-sm text-red-400/80">{result.details}</p>
        </div>
      )}
    </div>
  );
}
