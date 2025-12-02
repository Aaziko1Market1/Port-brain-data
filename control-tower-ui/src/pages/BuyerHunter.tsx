import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Target, TrendingUp, AlertTriangle, 
  Users, Bot, Loader2, ChevronRight 
} from 'lucide-react';
import { api, BuyerHunterResult } from '../api/client';

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

function ScoreBar({ score, max = 100 }: { score: number; max?: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const color = pct >= 70 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : pct >= 30 ? 'bg-orange-500' : 'bg-red-500';
  
  return (
    <div className="flex items-center space-x-2">
      <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-medium text-gray-700">{score.toFixed(1)}</span>
    </div>
  );
}

function formatValue(value: number | null): string {
  if (value === null || value === 0) return '-';
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function BuyerHunter() {
  const navigate = useNavigate();
  
  // Filter state
  const [hsCode, setHsCode] = useState('');
  const [country, setCountry] = useState('');
  const [monthsLookback, setMonthsLookback] = useState(12);
  const [minValue, setMinValue] = useState(50000);
  const [maxRiskLevel, setMaxRiskLevel] = useState('MEDIUM');
  const [searchMode, setSearchMode] = useState<'top' | 'byName'>('top');
  const [buyerNameSearch, setBuyerNameSearch] = useState('');
  
  // Search state
  const [searchParams, setSearchParams] = useState<{
    hs_code_6: string;
    destination_countries?: string;
    months_lookback: number;
    min_total_value_usd: number;
    max_risk_level: string;
    buyer_name?: string;
    mode: 'top' | 'byName';
  } | null>(null);
  
  // Selected buyer for AI
  const [selectedBuyer, setSelectedBuyer] = useState<BuyerHunterResult | null>(null);
  
  // Query - normalize response to have consistent shape
  const { data, isLoading, error } = useQuery({
    queryKey: ['buyer-hunter', searchParams],
    queryFn: async (): Promise<{ items: BuyerHunterResult[]; count: number } | null> => {
      if (!searchParams) return null;
      if (searchParams.mode === 'byName' && searchParams.buyer_name) {
        const res = await api.searchBuyerHunterByName({
          buyer_name: searchParams.buyer_name,
          hs_code_6: searchParams.hs_code_6,
          destination_countries: searchParams.destination_countries,
          months_lookback: searchParams.months_lookback,
          min_total_value_usd: searchParams.min_total_value_usd,
          max_risk_level: searchParams.max_risk_level,
          limit: 50
        });
        return { items: res.items, count: res.total };
      }
      const res = await api.getBuyerHunterTop({
        hs_code_6: searchParams.hs_code_6,
        destination_countries: searchParams.destination_countries,
        months_lookback: searchParams.months_lookback,
        min_total_value_usd: searchParams.min_total_value_usd,
        max_risk_level: searchParams.max_risk_level,
        limit: 30
      });
      return { items: res.items, count: res.count };
    },
    enabled: !!searchParams,
  });
  
  // AI explain mutation
  const explainMutation = useMutation({
    mutationFn: (buyerUuid: string) => api.explainBuyer(buyerUuid, 'sales'),
  });
  
  const handleSearch = () => {
    if (!hsCode || hsCode.length !== 6 || !/^\d+$/.test(hsCode)) {
      alert('Please enter a valid 6-digit HS code');
      return;
    }
    
    if (searchMode === 'byName' && buyerNameSearch.length < 2) {
      alert('Please enter at least 2 characters for buyer name search');
      return;
    }
    
    setSearchParams({
      hs_code_6: hsCode,
      destination_countries: country || undefined,
      months_lookback: monthsLookback,
      min_total_value_usd: searchMode === 'byName' ? 10000 : minValue, // Lower threshold for name search
      max_risk_level: searchMode === 'byName' ? 'ALL' : maxRiskLevel, // All risk levels for name search
      buyer_name: searchMode === 'byName' ? buyerNameSearch : undefined,
      mode: searchMode
    });
    setSelectedBuyer(null);
  };
  
  const handleRowClick = (buyer: BuyerHunterResult) => {
    setSelectedBuyer(buyer);
  };
  
  const handleViewBuyer360 = (buyerUuid: string) => {
    navigate(`/buyers/${buyerUuid}`);
  };
  
  const handleAskAI = (buyer: BuyerHunterResult) => {
    explainMutation.mutate(buyer.buyer_uuid);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-purple-100 rounded-lg">
          <Target className="h-6 w-6 text-purple-600" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Buyer Hunter</h2>
          <p className="text-gray-500">Find the best target buyers for your HS code</p>
        </div>
      </div>

      {/* Filters Panel */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Search Filters</h3>
          
          {/* Search Mode Toggle */}
          <div className="flex items-center space-x-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setSearchMode('top')}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                searchMode === 'top' 
                  ? 'bg-white text-purple-600 shadow-sm font-medium' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Top Buyers
            </button>
            <button
              onClick={() => setSearchMode('byName')}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                searchMode === 'byName' 
                  ? 'bg-white text-purple-600 shadow-sm font-medium' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Search by Name
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-5 gap-4">
          {/* HS Code */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">HS Code (6-digit) *</label>
            <input
              type="text"
              placeholder="e.g., 690721"
              value={hsCode}
              onChange={(e) => setHsCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          
          {/* Country */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Destination Country</label>
            <input
              type="text"
              placeholder="e.g., KENYA"
              value={country}
              onChange={(e) => setCountry(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          
          {/* Buyer Name Search - shown in "byName" mode */}
          {searchMode === 'byName' && (
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Buyer Name *</label>
              <input
                type="text"
                placeholder="e.g., DAVITA"
                value={buyerNameSearch}
                onChange={(e) => setBuyerNameSearch(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 border border-purple-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-purple-50"
              />
              <p className="text-xs text-purple-600 mt-1">Search for specific buyers by name (partial match)</p>
            </div>
          )}
          
          {/* Months Lookback */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Months Lookback</label>
            <select
              value={monthsLookback}
              onChange={(e) => setMonthsLookback(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value={6}>6 months</option>
              <option value={12}>12 months</option>
              <option value={24}>24 months</option>
              <option value={36}>36 months</option>
            </select>
          </div>
          
          {/* Min Value */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Min Total Value</label>
            <select
              value={minValue}
              onChange={(e) => setMinValue(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value={10000}>$10K+</option>
              <option value={50000}>$50K+</option>
              <option value={100000}>$100K+</option>
              <option value={500000}>$500K+</option>
              <option value={1000000}>$1M+</option>
            </select>
          </div>
          
          {/* Max Risk Level */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Max Risk Level</label>
            <select
              value={maxRiskLevel}
              onChange={(e) => setMaxRiskLevel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="LOW">Low only</option>
              <option value="MEDIUM">Low + Medium</option>
              <option value="HIGH">Low + Medium + High</option>
              <option value="ALL">All levels</option>
            </select>
          </div>
        </div>
        
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleSearch}
            disabled={!hsCode || hsCode.length !== 6}
            className="flex items-center space-x-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Search className="h-4 w-4" />
            <span>Search Buyers</span>
          </button>
        </div>
      </div>

      {/* Results */}
      {searchParams && (
        <div className="grid grid-cols-3 gap-6">
          {/* Results Table */}
          <div className="col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Users className="h-5 w-5 text-gray-400" />
                <h3 className="font-semibold text-gray-900">
                  Top Buyers for HS {searchParams.hs_code_6}
                </h3>
              </div>
              {data && (
                <span className="text-sm text-gray-500">{data.count} results</span>
              )}
            </div>
            
            {error ? (
              <div className="p-8 text-center text-red-600">
                Error loading results. Please try again.
              </div>
            ) : isLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
              </div>
            ) : data?.items.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No buyers found matching your criteria.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Buyer</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">12m Value</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">HS Share</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data?.items.map((buyer, idx) => (
                      <tr
                        key={buyer.buyer_uuid}
                        onClick={() => handleRowClick(buyer)}
                        className={`cursor-pointer transition-colors ${
                          selectedBuyer?.buyer_uuid === buyer.buyer_uuid
                            ? 'bg-purple-50'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center space-x-2">
                            <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 text-xs flex items-center justify-center font-medium">
                              {idx + 1}
                            </span>
                            <div>
                              <p className="font-medium text-gray-900 text-sm">{buyer.buyer_name}</p>
                              <p className="text-xs text-gray-500">{buyer.destination_country || buyer.buyer_country}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">
                          {formatValue(buyer.total_value_usd_12m)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 text-right">
                          {buyer.hs_share_pct.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-center">
                          <RiskBadge level={buyer.current_risk_level} />
                        </td>
                        <td className="px-4 py-3">
                          <ScoreBar score={buyer.opportunity_score} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Selected Buyer Detail Panel */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            {selectedBuyer ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">{selectedBuyer.buyer_name}</h3>
                  <button
                    onClick={() => handleViewBuyer360(selectedBuyer.buyer_uuid)}
                    className="flex items-center text-sm text-purple-600 hover:text-purple-700"
                  >
                    View 360 <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
                
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Country</span>
                    <span className="font-medium">{selectedBuyer.destination_country || selectedBuyer.buyer_country || '-'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">12m Value</span>
                    <span className="font-medium">{formatValue(selectedBuyer.total_value_usd_12m)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Shipments</span>
                    <span className="font-medium">{selectedBuyer.total_shipments_12m}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Avg Shipment</span>
                    <span className="font-medium">{formatValue(selectedBuyer.avg_shipment_value_usd)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">HS Share</span>
                    <span className="font-medium">{selectedBuyer.hs_share_pct.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Months Active</span>
                    <span className="font-medium">{selectedBuyer.months_with_shipments_12m}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Years Active</span>
                    <span className="font-medium">{selectedBuyer.years_active}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Classification</span>
                    <span className="font-medium">{selectedBuyer.classification}</span>
                  </div>
                </div>
                
                {/* Score Breakdown */}
                <div className="pt-4 border-t border-gray-100">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Score Breakdown</h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Volume (40 max)</span>
                      <span>{selectedBuyer.volume_score}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Stability (20 max)</span>
                      <span>{selectedBuyer.stability_score}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">HS Focus (15 max)</span>
                      <span>{selectedBuyer.hs_focus_score}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Risk (15 max)</span>
                      <span>{selectedBuyer.risk_score_component}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Data Quality (10 max)</span>
                      <span>{selectedBuyer.data_quality_score}</span>
                    </div>
                    <div className="flex justify-between font-medium text-gray-900 pt-2 border-t">
                      <span>Total Score</span>
                      <span>{selectedBuyer.opportunity_score}</span>
                    </div>
                  </div>
                </div>
                
                {/* AI Helper */}
                <div className="pt-4 border-t border-gray-100">
                  <button
                    onClick={() => handleAskAI(selectedBuyer)}
                    disabled={explainMutation.isPending}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
                  >
                    {explainMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                    <span>Ask AI: Why is this buyer interesting?</span>
                  </button>
                  
                  {explainMutation.data && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                      <pre className="whitespace-pre-wrap text-xs text-gray-700 font-sans">
                        {explainMutation.data.explanation}
                      </pre>
                    </div>
                  )}
                  
                  {explainMutation.error && (
                    <div className="mt-3 p-3 bg-red-50 rounded-lg text-xs text-red-600">
                      Failed to get AI explanation. Please try again.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-gray-400 py-12">
                <Target className="h-12 w-12 mb-3" />
                <p className="text-sm">Select a buyer to view details</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Initial State */}
      {!searchParams && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <Target className="h-16 w-16 text-purple-200 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Find Your Best Buyers</h3>
          <p className="text-gray-500 max-w-md mx-auto">
            Enter an HS code and filters above to discover the highest-opportunity buyers 
            based on trade volume, stability, and risk profile.
          </p>
          <div className="mt-6 flex items-center justify-center space-x-8 text-sm text-gray-500">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4 text-green-500" />
              <span>Volume-based scoring</span>
            </div>
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              <span>Risk-adjusted</span>
            </div>
            <div className="flex items-center space-x-2">
              <Bot className="h-4 w-4 text-blue-500" />
              <span>AI explanations</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
