import { useQuery } from '@tanstack/react-query';
import { getDashboardOverview } from '../api/dashboard';
import { listDatasets } from '../api/datasets';
import { Link } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { Database, CheckCircle, XCircle, Clock } from 'lucide-react';

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
    return <div className="text-gray-500">Loading dashboard...</div>;
  }

  if (!overview) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-gray-300 mb-4">Welcome to ForgeRunner</h2>
        <p className="text-gray-500 mb-6">Upload a JSONL file to get started</p>
        <Link to="/upload" className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600">
          Upload Dataset
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={<Database className="w-5 h-5" />} label="Total Examples" value={overview.total_examples} color="text-blue-400" />
        <StatCard icon={<CheckCircle className="w-5 h-5" />} label="Approved" value={overview.approved_count} color="text-green-400" />
        <StatCard icon={<XCircle className="w-5 h-5" />} label="Rejected" value={overview.rejected_count} color="text-red-400" />
        <StatCard icon={<Clock className="w-5 h-5" />} label="Pending" value={overview.pending_count} color="text-yellow-400" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Score Distribution */}
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Score Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={overview.score_distribution}>
              <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <Tooltip contentStyle={{ background: '#1F2937', border: '1px solid #374151', borderRadius: 8 }} />
              <Bar dataKey="count" fill="#F97316" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Bucket Breakdown */}
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Bucket Breakdown</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={overview.bucket_breakdown.filter(b => b.count > 0)}
                dataKey="count"
                nameKey="display_name"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ display_name, count }) => `${display_name} (${count})`}
                labelLine={false}
              >
                {overview.bucket_breakdown.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1F2937', border: '1px solid #374151', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
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

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className={`flex items-center gap-2 mb-2 ${color}`}>{icon}<span className="text-xs uppercase tracking-wider text-gray-500">{label}</span></div>
      <div className="text-2xl font-bold">{value.toLocaleString()}</div>
    </div>
  );
}

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
