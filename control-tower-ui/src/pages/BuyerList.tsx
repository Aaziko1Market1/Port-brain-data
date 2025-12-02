import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { api, BuyerSummary } from '../api/client';

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-700',
    MEDIUM: 'bg-yellow-100 text-yellow-700',
    HIGH: 'bg-orange-100 text-orange-700',
    CRITICAL: 'bg-red-100 text-red-700',
    UNSCORED: 'bg-gray-100 text-gray-600',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[level] || colors.UNSCORED}`}>
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

export default function BuyerList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [filters, setFilters] = useState({
    country: searchParams.get('country') || '',
    risk_level: searchParams.get('risk_level') || '',
    hs_code_6: searchParams.get('hs_code_6') || '',
  });
  
  const [debouncedHsCode, setDebouncedHsCode] = useState(filters.hs_code_6);
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'));
  const limit = 20;

  // Debounce HS code filter
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedHsCode(filters.hs_code_6);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [filters.hs_code_6]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['buyers', filters.country, filters.risk_level, debouncedHsCode, page],
    queryFn: () => api.getBuyers({
      country: filters.country || undefined,
      risk_level: filters.risk_level || undefined,
      hs_code_6: debouncedHsCode || undefined,
      limit,
      offset: (page - 1) * limit,
    }),
  });

  const totalPages = Math.ceil((data?.total || 0) / limit);

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    if (key !== 'hs_code_6') setPage(1);
    
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    newParams.set('page', '1');
    setSearchParams(newParams);
  };

  const handleRowClick = (buyer: BuyerSummary) => {
    navigate(`/buyers/${buyer.buyer_uuid}`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Buyers</h2>
        <p className="text-gray-500 mt-1">Browse and filter buyer profiles</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-gray-400" />
          
          <div className="flex-1 grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Country</label>
              <select
                value={filters.country}
                onChange={(e) => handleFilterChange('country', e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Countries</option>
                <option value="KENYA">Kenya</option>
                <option value="INDIA">India</option>
                <option value="INDONESIA">Indonesia</option>
              </select>
            </div>
            
            <div>
              <label className="block text-xs text-gray-500 mb-1">Risk Level</label>
              <select
                value={filters.risk_level}
                onChange={(e) => handleFilterChange('risk_level', e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Levels</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
                <option value="UNSCORED">Unscored</option>
              </select>
            </div>
            
            <div>
              <label className="block text-xs text-gray-500 mb-1">HS Code</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Filter by HS code..."
                  value={filters.hs_code_6}
                  onChange={(e) => handleFilterChange('hs_code_6', e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {error ? (
          <div className="p-8 text-center text-red-600">
            Error loading buyers. Please try again.
          </div>
        ) : isLoading ? (
          <div className="p-8">
            <div className="animate-pulse space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-100 rounded" />
              ))}
            </div>
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Buyer Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Country</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Value</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Shipments</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.items.map((buyer) => (
                  <tr
                    key={buyer.buyer_uuid}
                    onClick={() => handleRowClick(buyer)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-gray-900">{buyer.buyer_name}</p>
                        <p className="text-xs text-gray-500">{buyer.buyer_classification || 'Unknown'}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {buyer.buyer_country || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 text-right font-medium">
                      {formatValue(buyer.total_value_usd)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 text-right">
                      {buyer.total_shipments.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <RiskBadge level={buyer.current_risk_level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Showing {((page - 1) * limit) + 1} to {Math.min(page * limit, data?.total || 0)} of {data?.total || 0} buyers
              </p>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-sm text-gray-600">
                  Page {page} of {totalPages || 1}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-2 rounded-lg border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
