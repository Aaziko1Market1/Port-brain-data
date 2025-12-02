import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Package, Users, Globe, Ship, TrendingUp, AlertTriangle } from 'lucide-react';
import { api } from '../api/client';

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  color = 'blue' 
}: { 
  title: string; 
  value: string | number; 
  icon: React.ElementType; 
  color?: string;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

function formatValue(value: number | null): string {
  if (value === null) return 'N/A';
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
  });

  const { data: topHsCodes, isLoading: hsLoading } = useQuery({
    queryKey: ['top-hs-codes'],
    queryFn: () => api.getTopHsCodes({ limit: 5 }),
  });

  const { data: riskSummary } = useQuery({
    queryKey: ['risk-summary'],
    queryFn: api.getRiskSummary,
  });

  const chartData = topHsCodes?.items.map((hs) => ({
    name: hs.hs_code_6,
    value: hs.total_value_usd || 0,
    shipments: hs.total_shipments,
  })) || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-gray-500 mt-1">Global Trade Intelligence Overview</p>
      </div>

      {/* Stats Grid */}
      {statsLoading ? (
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl h-28 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            title="Total Shipments"
            value={stats?.total_shipments || 0}
            icon={Ship}
            color="blue"
          />
          <StatCard
            title="Total Buyers"
            value={stats?.total_buyers || 0}
            icon={Users}
            color="green"
          />
          <StatCard
            title="Countries"
            value={stats?.total_countries || 0}
            icon={Globe}
            color="purple"
          />
          <StatCard
            title="HS Codes"
            value={stats?.total_hs_codes || 0}
            icon={Package}
            color="orange"
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Top HS Codes Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Top 5 HS Codes by Value</h3>
            <TrendingUp className="h-5 w-5 text-gray-400" />
          </div>
          {hsLoading ? (
            <div className="h-64 bg-gray-50 rounded animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                <XAxis 
                  type="number" 
                  tickFormatter={(v) => formatValue(v)}
                  fontSize={12}
                />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  width={70}
                  fontSize={12}
                />
                <Tooltip 
                  formatter={(value: number) => [formatValue(value), 'Value']}
                  labelFormatter={(label) => `HS Code: ${label}`}
                />
                <Bar dataKey="value" fill="#3B82F6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Risk Summary */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Risk Distribution</h3>
            <AlertTriangle className="h-5 w-5 text-gray-400" />
          </div>
          
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-2">Shipment Risks</h4>
              <div className="grid grid-cols-4 gap-2">
                {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => {
                  const count = riskSummary?.SHIPMENT[level] || 0;
                  const colors: Record<string, string> = {
                    LOW: 'bg-green-100 text-green-700',
                    MEDIUM: 'bg-yellow-100 text-yellow-700',
                    HIGH: 'bg-orange-100 text-orange-700',
                    CRITICAL: 'bg-red-100 text-red-700',
                  };
                  return (
                    <div key={level} className={`p-3 rounded-lg ${colors[level]}`}>
                      <p className="text-xs font-medium">{level}</p>
                      <p className="text-lg font-bold">{count}</p>
                    </div>
                  );
                })}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-2">Buyer Risks</h4>
              <div className="grid grid-cols-4 gap-2">
                {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => {
                  const count = riskSummary?.BUYER[level] || 0;
                  const colors: Record<string, string> = {
                    LOW: 'bg-green-100 text-green-700',
                    MEDIUM: 'bg-yellow-100 text-yellow-700',
                    HIGH: 'bg-orange-100 text-orange-700',
                    CRITICAL: 'bg-red-100 text-red-700',
                  };
                  return (
                    <div key={level} className={`p-3 rounded-lg ${colors[level]}`}>
                      <p className="text-xs font-medium">{level}</p>
                      <p className="text-lg font-bold">{count}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline Status */}
      {stats?.last_pipeline_runs && stats.last_pipeline_runs.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Pipeline Status</h3>
          <div className="grid grid-cols-5 gap-4">
            {stats.last_pipeline_runs.map((run) => (
              <div key={run.pipeline_name} className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-900 capitalize">
                  {run.pipeline_name.replace(/_/g, ' ')}
                </p>
                <p className={`text-xs mt-1 ${
                  run.status === 'SUCCESS' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {run.status}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {run.rows_processed?.toLocaleString() || 0} rows
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
