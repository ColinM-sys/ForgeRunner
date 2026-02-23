import { useEffect, useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDashboardOverview } from '../api/dashboard';
import { listDatasets } from '../api/datasets';
import { listExamples, type ExampleFilters } from '../api/examples';
import { Link } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import { Database, CheckCircle, XCircle, Clock, Gauge, ChevronDown, Trash2 } from 'lucide-react';
import type { Example } from '../types';

const TOOLTIP_STYLE = {
  contentStyle: { background: '#111827', border: '1px solid #374151', borderRadius: 8, color: '#E5E7EB', fontSize: 13 },
  cursor: { fill: 'rgba(255,255,255,0.05)' },
};

// Color gradient for score bars: red -> yellow -> green
const SCORE_COLORS = [
  '#EF4444', '#F87171', '#FB923C', '#FBBF24', '#FACC15',
  '#A3E635', '#84CC16', '#4ADE80', '#22C55E', '#16A34A',
];

export default function DashboardPage() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: getDashboardOverview,
  });

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasets,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="text-center py-20">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-orange-500/10 flex items-center justify-center">
          <Database className="w-10 h-10 text-orange-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-300 mb-2">Welcome to ForgeRunner</h2>
        <p className="text-gray-500 mb-8">Upload a JSONL training file to analyze data quality</p>
        <Link to="/upload" className="bg-orange-500 text-white px-8 py-3 rounded-xl hover:bg-orange-600 font-medium transition-colors">
          Upload Dataset
        </Link>
      </div>
    );
  }

  // Build radar data from engine coverage
  const radarData = Object.entries(overview.engine_coverage).map(([engine, count]) => ({
    engine: engine === 'forge_embedder' ? 'ForgeEmbedder' : engine.charAt(0).toUpperCase() + engine.slice(1),
    coverage: overview.total_examples > 0 ? Math.round((count / overview.total_examples) * 100) : 0,
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* Stats cards with animated counters */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={<Database className="w-5 h-5" />} label="Total Examples" value={overview.total_examples} color="blue" />
        <StatCard icon={<CheckCircle className="w-5 h-5" />} label="Approved" value={overview.approved_count} color="green" />
        <StatCard icon={<XCircle className="w-5 h-5" />} label="Rejected" value={overview.rejected_count} color="red" />
        <StatCard icon={<Clock className="w-5 h-5" />} label="Pending" value={overview.pending_count} color="yellow" />
      </div>

      {/* Quality Gauge + Engine Radar */}
      <div className="grid grid-cols-3 gap-6">
        {/* Quality Gauge */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 flex flex-col items-center justify-center">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Overall Quality</h3>
          <QualityGauge score={overview.average_score} />
          <div className="mt-3 text-center">
            <p className="text-xs text-gray-500">Approval Rate</p>
            <p className="text-lg font-bold text-gray-300">{overview.approval_rate}%</p>
          </div>
        </div>

        {/* Score Distribution with clickable bars */}
        <ScoreDistributionPanel distribution={overview.score_distribution} />

        {/* Engine Coverage Radar */}
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Engine Coverage</h3>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={230}>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="engine" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                <PolarRadiusAxis tick={{ fontSize: 9, fill: '#6B7280' }} domain={[0, 100]} />
                <Radar name="Coverage %" dataKey="coverage" stroke="#F97316" fill="#F97316" fillOpacity={0.2} strokeWidth={2} />
                <Tooltip {...TOOLTIP_STYLE} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[230px] flex items-center justify-center text-gray-600 text-sm">
              No scoring data yet
            </div>
          )}
        </div>
      </div>

      {/* Donut Chart */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Bucket Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={overview.bucket_breakdown.filter(b => b.count > 0)}
                dataKey="count"
                nameKey="display_name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={95}
                paddingAngle={2}
                label={({ display_name, count, percent }) => `${display_name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: '#4B5563', strokeWidth: 1 }}
              >
                {overview.bucket_breakdown.filter(b => b.count > 0).map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip {...TOOLTIP_STYLE} />
              {/* Center text */}
              <text x="50%" y="47%" textAnchor="middle" fill="#E5E7EB" fontSize={22} fontWeight="bold">
                {overview.total_examples.toLocaleString()}
              </text>
              <text x="50%" y="57%" textAnchor="middle" fill="#6B7280" fontSize={11}>
                total examples
              </text>
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Review Status Breakdown */}
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Review Progress</h3>
          <div className="space-y-4 mt-6">
            <ProgressBar label="Approved" count={overview.approved_count} total={overview.total_examples} color="bg-green-500" />
            <ProgressBar label="Rejected" count={overview.rejected_count} total={overview.total_examples} color="bg-red-500" />
            <ProgressBar label="Pending" count={overview.pending_count} total={overview.total_examples} color="bg-yellow-500" />
          </div>
          <div className="mt-8 pt-4 border-t border-gray-800 flex justify-between text-sm">
            <span className="text-gray-500">Datasets</span>
            <span className="font-medium">{overview.total_datasets}</span>
          </div>
          {overview.average_score !== null && (
            <div className="flex justify-between text-sm mt-2">
              <span className="text-gray-500">Avg Quality Score</span>
              <span className="font-medium">{overview.average_score.toFixed(3)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Datasets list */}
      {datasets && datasets.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Datasets</h3>
          <div className="space-y-2">
            {datasets.map((ds) => (
              <Link
                key={ds.id}
                to={`/datasets/${ds.id}`}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
              >
                <div>
                  <span className="font-medium">{ds.name}</span>
                  <span className="text-gray-500 text-sm ml-3">{ds.filename}</span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-gray-400">{ds.total_examples.toLocaleString()} examples</span>
                  <StatusBadge status={ds.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Score Distribution Panel (clickable bars → lowest quality examples) ─── */
function ScoreDistributionPanel({ distribution }: { distribution: { range: string; count: number }[] }) {
  const [selectedRange, setSelectedRange] = useState<string | null>(null);
  const [examples, setExamples] = useState<Example[]>([]);
  const [loading, setLoading] = useState(false);

  // Parse range string like "0.0-0.1" to min/max
  const parseRange = (range: string) => {
    const parts = range.split('-');
    return { min: parseFloat(parts[0]), max: parseFloat(parts[1]) };
  };

  const handleBarClick = async (data: { range?: string; activeLabel?: string } | null) => {
    if (!data) return;
    const range = data.range || data.activeLabel;
    if (!range) return;

    if (selectedRange === range) {
      setSelectedRange(null);
      setExamples([]);
      return;
    }

    setSelectedRange(range);
    setLoading(true);

    try {
      const { min, max } = parseRange(range);
      const result = await listExamples({
        min_score: min,
        max_score: max,
        sort_by: 'aggregate_score',
        sort_order: 'asc',
        page_size: 10,
      });
      setExamples(result.items);
    } catch {
      setExamples([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-400">Score Distribution</h3>
        <span className="text-[10px] text-gray-600">Click a bar to see examples</span>
      </div>
      <ResponsiveContainer width="100%" height={230}>
        <BarChart data={distribution} onClick={(e) => handleBarClick(e?.activePayload?.[0]?.payload)}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
          <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={{ stroke: '#374151' }} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
          <Tooltip {...TOOLTIP_STYLE} />
          {distribution.map((_, i) => (
            <Bar key={i} dataKey="count" radius={[4, 4, 0, 0]} style={{ cursor: 'pointer' }}>
              {distribution.map((entry, j) => (
                <Cell
                  key={j}
                  fill={selectedRange === entry.range ? '#F97316' : SCORE_COLORS[j]}
                  stroke={selectedRange === entry.range ? '#FB923C' : 'transparent'}
                  strokeWidth={selectedRange === entry.range ? 2 : 0}
                />
              ))}
            </Bar>
          )).slice(0, 1)}
        </BarChart>
      </ResponsiveContainer>

      {/* Expanded: lowest quality examples in selected range */}
      {selectedRange && (
        <div className="mt-3 border-t border-gray-800 pt-3">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-semibold text-gray-500">
              Lowest Quality in <span className="text-orange-400">{selectedRange}</span>
            </h4>
            <button
              onClick={() => { setSelectedRange(null); setExamples([]); }}
              className="text-[10px] text-gray-600 hover:text-gray-400"
            >
              Close
            </button>
          </div>

          {loading ? (
            <div className="text-xs text-gray-600 py-4 text-center">Loading...</div>
          ) : examples.length === 0 ? (
            <div className="text-xs text-gray-600 py-4 text-center">No examples in this range</div>
          ) : (
            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {examples.map((ex, i) => (
                <Link
                  key={ex.id}
                  to={`/datasets/${ex.dataset_id}`}
                  className="flex items-start gap-2 p-2 rounded-lg bg-gray-800/40 hover:bg-gray-800 transition-colors group"
                >
                  <span className="text-[10px] text-gray-600 font-mono mt-0.5 shrink-0">#{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-400 truncate">
                      {ex.user_content?.slice(0, 120) || '(empty)'}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {ex.bucket_name && (
                        <span className="text-[10px] text-gray-600">{ex.bucket_name}</span>
                      )}
                      <span className="text-[10px] text-gray-600">Line {ex.line_number}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span className={`text-xs font-mono font-bold ${
                      (ex.aggregate_score ?? 0) >= 0.7 ? 'text-green-400' :
                      (ex.aggregate_score ?? 0) >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {ex.aggregate_score !== null ? (ex.aggregate_score * 100).toFixed(0) : '--'}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Animated Counter ─── */
function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<number | null>(null);

  useEffect(() => {
    const duration = 800;
    const start = ref.current ?? 0;
    const diff = value - start;
    const startTime = performance.now();

    function step(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + diff * eased);
      setDisplay(current);
      if (progress < 1) requestAnimationFrame(step);
      else ref.current = value;
    }
    requestAnimationFrame(step);
  }, [value]);

  return <>{display.toLocaleString()}</>;
}

/* ─── Stat Card ─── */
function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  const colorMap: Record<string, { text: string; bg: string; border: string }> = {
    blue:   { text: 'text-blue-400',   bg: 'bg-blue-500/5',   border: 'border-blue-500/20' },
    green:  { text: 'text-green-400',  bg: 'bg-green-500/5',  border: 'border-green-500/20' },
    red:    { text: 'text-red-400',    bg: 'bg-red-500/5',    border: 'border-red-500/20' },
    yellow: { text: 'text-yellow-400', bg: 'bg-yellow-500/5', border: 'border-yellow-500/20' },
  };
  const c = colorMap[color] || colorMap.blue;

  return (
    <div className={`rounded-xl p-4 border ${c.border} ${c.bg} transition-all hover:scale-[1.02]`}>
      <div className={`flex items-center gap-2 mb-2 ${c.text}`}>
        {icon}
        <span className="text-xs uppercase tracking-wider text-gray-500">{label}</span>
      </div>
      <div className="text-2xl font-bold">
        <AnimatedNumber value={value} />
      </div>
    </div>
  );
}

/* ─── Quality Gauge ─── */
function QualityGauge({ score }: { score: number | null }) {
  const value = score !== null ? score : 0;
  const percentage = Math.round(value * 100);
  const rotation = -90 + (value * 180); // -90 to 90 degrees

  const getColor = (v: number) => {
    if (v >= 0.7) return '#22C55E';
    if (v >= 0.4) return '#FBBF24';
    return '#EF4444';
  };
  const color = getColor(value);

  // SVG arc for semicircle gauge
  const radius = 60;
  const cx = 70;
  const cy = 70;
  const circumference = Math.PI * radius;
  const offset = circumference - (value * circumference);

  return (
    <div className="relative">
      <svg width="140" height="85" viewBox="0 0 140 85">
        {/* Background arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="#1F2937"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s ease-out, stroke 0.5s' }}
        />
        {/* Score text */}
        <text x={cx} y={cy - 8} textAnchor="middle" fill={color} fontSize="28" fontWeight="bold">
          {score !== null ? percentage : '--'}
        </text>
        <text x={cx} y={cy + 8} textAnchor="middle" fill="#6B7280" fontSize="10">
          / 100
        </text>
      </svg>
    </div>
  );
}

/* ─── Progress Bar ─── */
function ProgressBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-300 font-medium">{count.toLocaleString()} <span className="text-gray-600">({pct.toFixed(1)}%)</span></span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all duration-1000 ease-out`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/* ─── Status Badge ─── */
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    uploading: 'bg-blue-500/20 text-blue-400',
    processing: 'bg-yellow-500/20 text-yellow-400',
    scored: 'bg-green-500/20 text-green-400',
    error: 'bg-red-500/20 text-red-400',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs ${colors[status] || 'bg-gray-700 text-gray-400'}`}>
      {status}
    </span>
  );
}
