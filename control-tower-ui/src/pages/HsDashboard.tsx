import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Search, Package, TrendingUp, Users, AlertTriangle } from 'lucide-react';
import { api } from '../api/client';

function formatValue(value: number | null): string {
  if (value === null) return '-';
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function HsDashboard() {
  const [hsCode, setHsCode] = useState('');
  const [searchedHsCode, setSearchedHsCode] = useState('');
  const [country, setCountry] = useState('');
  const [direction, setDirection] = useState('');

  const { data: topHsCodes, isLoading: topLoading } = useQuery({
    queryKey: ['top-hs-codes', country, direction],
    queryFn: () => api.getTopHsCodes({ 
      reporting_country: country || undefined, 
      direction: direction || undefined,
      limit: 10 
    }),
  });

  const { data: dashboard, isLoading: dashboardLoading, error } = useQuery({
    queryKey: ['hs-dashboard', searchedHsCode, country, direction],
    queryFn: () => api.getHsDashboard({
      hs_code_6: searchedHsCode,
      reporting_country: country || undefined,
      direction: direction || undefined,
    }),
    enabled: !!searchedHsCode,
  });

  const handleSearch = () => {
    if (hsCode.trim()) {
      setSearchedHsCode(hsCode.trim());
    }
  };

  const handleQuickSelect = (code: string) => {
    setHsCode(code);
    setSearchedHsCode(code);
  };

  const chartData = dashboard?.monthly_trend.map((m) => ({
    month: `${m.year}-${String(m.month).padStart(2, '0')}`,
    value: m.total_value_usd || 0,
    shipments: m.shipment_count,
  })) || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">HS Code Dashboard</h2>
        <p className="text-gray-500 mt-1">Analyze trade by HS code, country, and direction</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">HS Code (6-digit)</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="e.g., 690721"
                value={hsCode}
                onChange={(e) => setHsCode(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-xs text-gray-500 mb-1">Country</label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Countries</option>
              <option value="KENYA">Kenya</option>
              <option value="INDIA">India</option>
              <option value="INDONESIA">Indonesia</option>
            </select>
          </div>
          
          <div>
            <label className="block text-xs text-gray-500 mb-1">Direction</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All</option>
              <option value="IMPORT">Import</option>
              <option value="EXPORT">Export</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={!hsCode.trim()}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Top HS Codes Quick Select */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Top HS Codes by Value</h3>
        {topLoading ? (
          <div className="h-32 bg-gray-50 rounded animate-pulse" />
        ) : (
          <div className="grid grid-cols-5 gap-3">
            {topHsCodes?.items.map((hs) => (
              <button
                key={hs.hs_code_6}
                onClick={() => handleQuickSelect(hs.hs_code_6)}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  searchedHsCode === hs.hs_code_6
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <p className="font-mono text-sm font-medium text-gray-900">{hs.hs_code_6}</p>
                <p className="text-xs text-gray-500 mt-1">{formatValue(hs.total_value_usd)}</p>
                <p className="text-xs text-gray-400">{hs.total_shipments.toLocaleString()} shipments</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Dashboard Results */}
      {searchedHsCode && (
        <>
          {error ? (
            <div className="bg-red-50 rounded-xl p-6 text-center text-red-600">
              Error loading dashboard data. Please try again.
            </div>
          ) : dashboardLoading ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="h-64 bg-gray-50 rounded animate-pulse" />
            </div>
          ) : dashboard ? (
            <>
              {/* Stats */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Total Value</p>
                      <p className="text-xl font-bold text-gray-900 mt-1">{formatValue(dashboard.total_value_usd)}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-green-500" />
                  </div>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Shipments</p>
                      <p className="text-xl font-bold text-gray-900 mt-1">{dashboard.total_shipments.toLocaleString()}</p>
                    </div>
                    <Package className="h-8 w-8 text-blue-500" />
                  </div>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">Unique Buyers</p>
                      <p className="text-xl font-bold text-gray-900 mt-1">{dashboard.unique_buyers.toLocaleString()}</p>
                    </div>
                    <Users className="h-8 w-8 text-purple-500" />
                  </div>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500">High Risk %</p>
                      <p className="text-xl font-bold text-gray-900 mt-1">
                        {dashboard.high_risk_pct?.toFixed(1) || 0}%
                      </p>
                    </div>
                    <AlertTriangle className="h-8 w-8 text-orange-500" />
                  </div>
                </div>
              </div>

              {/* Chart */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="font-semibold text-gray-900 mb-4">
                  Monthly Trend for HS {searchedHsCode}
                </h3>
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="month" fontSize={12} />
                      <YAxis 
                        tickFormatter={(v) => formatValue(v)} 
                        fontSize={12}
                        width={80}
                      />
                      <Tooltip 
                        formatter={(value: number) => [formatValue(value), 'Value']}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#3B82F6" 
                        strokeWidth={2}
                        dot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-gray-500 text-center py-12">No trend data available</p>
                )}
              </div>

              {/* Monthly Breakdown Table */}
              {dashboard.monthly_data.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100">
                    <h3 className="font-semibold text-gray-900">Monthly Breakdown</h3>
                  </div>
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Shipments</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {dashboard.monthly_data.slice(0, 12).map((m, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-6 py-3 text-sm text-gray-900">
                            {m.year}-{String(m.month).padStart(2, '0')}
                          </td>
                          <td className="px-6 py-3 text-sm text-gray-600 text-right">
                            {m.shipment_count.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-sm text-gray-900 text-right font-medium">
                            {formatValue(m.total_value_usd)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
