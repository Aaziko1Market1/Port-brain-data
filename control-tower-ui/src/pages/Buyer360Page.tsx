import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { 
  ArrowLeft, Building2, MapPin, Package, Ship, 
  TrendingUp, AlertTriangle, Bot, Send, Loader2 
} from 'lucide-react';
import { api } from '../api/client';

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-700 border-green-200',
    MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    HIGH: 'bg-orange-100 text-orange-700 border-orange-200',
    CRITICAL: 'bg-red-100 text-red-700 border-red-200',
    UNSCORED: 'bg-gray-100 text-gray-600 border-gray-200',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${colors[level] || colors.UNSCORED}`}>
      {level}
    </span>
  );
}

function formatValue(value: number | null): string {
  if (value === null) return '-';
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatWeight(value: number | null): string {
  if (value === null) return '-';
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M kg`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K kg`;
  return `${value.toFixed(0)} kg`;
}

export default function Buyer360Page() {
  const { buyerUuid } = useParams<{ buyerUuid: string }>();
  const [aiQuestion, setAiQuestion] = useState('');
  const [selectedUseCase, setSelectedUseCase] = useState<'sales' | 'risk' | 'general'>('sales');

  const { data: buyer, isLoading, error } = useQuery({
    queryKey: ['buyer-360', buyerUuid],
    queryFn: () => api.getBuyer360(buyerUuid!),
    enabled: !!buyerUuid,
  });

  const { data: aiStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: api.getAIStatus,
  });

  const explainMutation = useMutation({
    mutationFn: () => api.explainBuyer(buyerUuid!, selectedUseCase),
  });

  const askMutation = useMutation({
    mutationFn: (question: string) => api.askAboutBuyer(buyerUuid!, question),
  });

  const handleAskQuestion = () => {
    if (aiQuestion.trim()) {
      askMutation.mutate(aiQuestion);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !buyer) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error loading buyer data</p>
        <Link to="/buyers" className="text-blue-600 hover:underline mt-2 inline-block">
          Back to Buyers
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        to="/buyers"
        className="inline-flex items-center text-gray-600 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Buyers
      </Link>

      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Building2 className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{buyer.buyer_name}</h1>
              <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                <span className="flex items-center">
                  <MapPin className="h-4 w-4 mr-1" />
                  {buyer.buyer_country || 'Unknown'}
                </span>
                <span>{buyer.buyer_classification || 'Unclassified'}</span>
              </div>
            </div>
          </div>
          <RiskBadge level={buyer.current_risk_level} />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Value</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{formatValue(buyer.total_value_usd)}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Shipments</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{buyer.total_shipments.toLocaleString()}</p>
            </div>
            <Ship className="h-8 w-8 text-blue-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Weight</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{formatWeight(buyer.total_qty_kg)}</p>
            </div>
            <Package className="h-8 w-8 text-purple-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Active Years</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{buyer.active_years}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-orange-500" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Top HS Codes */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Top HS Codes</h3>
          <div className="space-y-3">
            {buyer.top_hs_codes.length > 0 ? (
              buyer.top_hs_codes.map((hs, i) => (
                <div key={hs.hs_code_6} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center font-medium">
                      {i + 1}
                    </span>
                    <span className="font-mono text-sm">{hs.hs_code_6}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{formatValue(hs.value_usd)}</p>
                    <p className="text-xs text-gray-500">{hs.share_pct?.toFixed(1)}%</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-sm">No HS code data available</p>
            )}
          </div>
        </div>

        {/* Top Origins */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Top Origin Countries</h3>
          <div className="space-y-3">
            {buyer.top_origin_countries.length > 0 ? (
              buyer.top_origin_countries.map((origin, i) => (
                <div key={origin.country} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="w-6 h-6 rounded-full bg-green-100 text-green-700 text-xs flex items-center justify-center font-medium">
                      {i + 1}
                    </span>
                    <span className="text-sm">{origin.country}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{formatValue(origin.value_usd)}</p>
                    <p className="text-xs text-gray-500">{origin.share_pct?.toFixed(1)}%</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-sm">No origin data available</p>
            )}
          </div>
        </div>
      </div>

      {/* Risk Details */}
      {buyer.current_risk_level !== 'UNSCORED' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center space-x-2 mb-4">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            <h3 className="font-semibold text-gray-900">Risk Assessment</h3>
          </div>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Risk Score</p>
              <p className="text-lg font-bold text-gray-900">{buyer.current_risk_score?.toFixed(1) || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Confidence</p>
              <p className="text-lg font-bold text-gray-900">{buyer.current_confidence_score?.toFixed(1) || '-'}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Main Reason</p>
              <p className="text-lg font-bold text-gray-900">{buyer.current_main_reason_code || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Ghost Flag</p>
              <p className="text-lg font-bold text-gray-900">{buyer.has_ghost_flag ? 'Yes' : 'No'}</p>
            </div>
          </div>
        </div>
      )}

      {/* AI Co-Pilot */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-100 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Bot className={`h-5 w-5 ${aiStatus?.available ? 'text-blue-600' : 'text-gray-400'}`} />
          <h3 className="font-semibold text-gray-900">AI Co-Pilot</h3>
          {aiStatus?.available && (
            <span className="text-xs text-gray-500">({aiStatus.model})</span>
          )}
        </div>

        {!aiStatus?.available ? (
          <p className="text-gray-500 text-sm">AI Co-Pilot is not available. Configure an LLM to enable AI features.</p>
        ) : (
          <div className="space-y-4">
            {/* Quick Explain Buttons */}
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-600">Quick explain:</span>
              {(['sales', 'risk', 'general'] as const).map((useCase) => (
                <button
                  key={useCase}
                  onClick={() => {
                    setSelectedUseCase(useCase);
                    explainMutation.mutate();
                  }}
                  disabled={explainMutation.isPending}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedUseCase === useCase
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                  } disabled:opacity-50`}
                >
                  {useCase.charAt(0).toUpperCase() + useCase.slice(1)}
                </button>
              ))}
            </div>

            {/* Custom Question */}
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="Ask a question about this buyer..."
                value={aiQuestion}
                onChange={(e) => setAiQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleAskQuestion}
                disabled={!aiQuestion.trim() || askMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {askMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>

            {/* AI Response */}
            {(explainMutation.isPending || askMutation.isPending) && (
              <div className="bg-white rounded-lg p-4 border border-gray-100">
                <div className="flex items-center space-x-2 text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">AI is thinking...</span>
                </div>
              </div>
            )}

            {(explainMutation.data || askMutation.data) && (
              <div className="bg-white rounded-lg p-4 border border-gray-100">
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
                    {explainMutation.data?.explanation || askMutation.data?.explanation}
                  </pre>
                </div>
              </div>
            )}

            {(explainMutation.error || askMutation.error) && (
              <div className="bg-red-50 rounded-lg p-4 border border-red-100">
                <p className="text-sm text-red-600">
                  Failed to get AI response. Please try again.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
