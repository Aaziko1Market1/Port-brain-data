import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle, Ship, Users, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../api/client';

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-700',
    MEDIUM: 'bg-yellow-100 text-yellow-700',
    HIGH: 'bg-orange-100 text-orange-700',
    CRITICAL: 'bg-red-100 text-red-700',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[level] || 'bg-gray-100 text-gray-600'}`}>
      {level}
    </span>
  );
}

function formatValue(value: number | null): string {
  if (value === null) return '-';
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function RiskOverview() {
  const [activeTab, setActiveTab] = useState<'shipments' | 'buyers'>('shipments');
  const [riskLevel, setRiskLevel] = useState('HIGH,CRITICAL');
  const [page, setPage] = useState(1);
  const limit = 20;

  const { data: summary } = useQuery({
    queryKey: ['risk-summary'],
    queryFn: api.getRiskSummary,
  });

  const { data: shipments, isLoading: shipmentsLoading } = useQuery({
    queryKey: ['risk-shipments', riskLevel, page],
    queryFn: () => api.getRiskShipments({
      level: riskLevel,
      limit,
      offset: (page - 1) * limit,
    }),
    enabled: activeTab === 'shipments',
  });

  const { data: buyers, isLoading: buyersLoading } = useQuery({
    queryKey: ['risk-buyers', riskLevel, page],
    queryFn: () => api.getRiskBuyers({
      level: riskLevel,
      limit,
      offset: (page - 1) * limit,
    }),
    enabled: activeTab === 'buyers',
  });

  const totalShipmentRisks = summary?.totals.SHIPMENT || 0;
  const totalBuyerRisks = summary?.totals.BUYER || 0;

  const currentData = activeTab === 'shipments' ? shipments : buyers;
  const totalPages = Math.ceil((currentData?.total || 0) / limit);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Risk Overview</h2>
        <p className="text-gray-500 mt-1">Monitor and analyze risk signals across shipments and buyers</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => {
          const shipmentCount = summary?.SHIPMENT[level] || 0;
          const buyerCount = summary?.BUYER[level] || 0;
          const colors: Record<string, { bg: string; text: string; icon: string }> = {
            LOW: { bg: 'bg-green-50', text: 'text-green-700', icon: 'text-green-500' },
            MEDIUM: { bg: 'bg-yellow-50', text: 'text-yellow-700', icon: 'text-yellow-500' },
            HIGH: { bg: 'bg-orange-50', text: 'text-orange-700', icon: 'text-orange-500' },
            CRITICAL: { bg: 'bg-red-50', text: 'text-red-700', icon: 'text-red-500' },
          };
          const color = colors[level];

          return (
            <div key={level} className={`${color.bg} rounded-xl p-5`}>
              <div className="flex items-center justify-between mb-3">
                <span className={`font-medium ${color.text}`}>{level}</span>
                <AlertTriangle className={`h-5 w-5 ${color.icon}`} />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Shipments</span>
                  <span className={`font-bold ${color.text}`}>{shipmentCount}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Buyers</span>
                  <span className={`font-bold ${color.text}`}>{buyerCount}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Tabs and Filter */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="flex items-center justify-between border-b border-gray-100 px-6">
          <div className="flex">
            <button
              onClick={() => { setActiveTab('shipments'); setPage(1); }}
              className={`flex items-center space-x-2 px-4 py-4 border-b-2 transition-colors ${
                activeTab === 'shipments'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Ship className="h-4 w-4" />
              <span>Risky Shipments ({totalShipmentRisks})</span>
            </button>
            <button
              onClick={() => { setActiveTab('buyers'); setPage(1); }}
              className={`flex items-center space-x-2 px-4 py-4 border-b-2 transition-colors ${
                activeTab === 'buyers'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Users className="h-4 w-4" />
              <span>Risky Buyers ({totalBuyerRisks})</span>
            </button>
          </div>
          
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-500">Level:</label>
            <select
              value={riskLevel}
              onChange={(e) => { setRiskLevel(e.target.value); setPage(1); }}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="HIGH,CRITICAL">High & Critical</option>
              <option value="CRITICAL">Critical Only</option>
              <option value="HIGH">High Only</option>
              <option value="MEDIUM">Medium Only</option>
              <option value="LOW,MEDIUM,HIGH,CRITICAL">All Levels</option>
            </select>
          </div>
        </div>

        {/* Table */}
        {activeTab === 'shipments' ? (
          shipmentsLoading ? (
            <div className="p-6">
              <div className="animate-pulse space-y-3">
                {[...Array(5)].map((_, i) => <div key={i} className="h-12 bg-gray-100 rounded" />)}
              </div>
            </div>
          ) : (
            <>
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">HS Code</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Route</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Value</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {shipments?.items.map((s) => (
                    <tr key={s.entity_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 font-mono text-sm">{s.hs_code_6 || '-'}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {s.origin_country || '?'} → {s.destination_country || '?'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right font-medium">
                        {formatValue(s.customs_value_usd)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <RiskBadge level={s.risk_level} />
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{s.main_reason_code}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right font-medium">
                        {s.risk_score.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  Showing {((page - 1) * limit) + 1} to {Math.min(page * limit, shipments?.total || 0)} of {shipments?.total || 0}
                </p>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-600">Page {page} of {totalPages || 1}</span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </>
          )
        ) : (
          buyersLoading ? (
            <div className="p-6">
              <div className="animate-pulse space-y-3">
                {[...Array(5)].map((_, i) => <div key={i} className="h-12 bg-gray-100 rounded" />)}
              </div>
            </div>
          ) : (
            <>
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Buyer</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Country</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Value</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {buyers?.items.map((b) => (
                    <tr key={b.entity_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <Link 
                          to={`/buyers/${b.entity_id}`}
                          className="text-blue-600 hover:underline font-medium"
                        >
                          {b.buyer_name || 'Unknown'}
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{b.buyer_country || '-'}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right font-medium">
                        {formatValue(b.total_value_usd)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <RiskBadge level={b.risk_level} />
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{b.main_reason_code}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right font-medium">
                        {b.risk_score.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  Showing {((page - 1) * limit) + 1} to {Math.min(page * limit, buyers?.total || 0)} of {buyers?.total || 0}
                </p>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-600">Page {page} of {totalPages || 1}</span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 hover:bg-gray-50"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </>
          )
        )}
      </div>
    </div>
  );
}
