/**
 * GTI-OS Control Tower API Client
 */

const API_BASE = '/api/v1';

export interface ApiError {
  error: string;
  detail?: string;
  status_code: number;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      error: 'Request failed',
      detail: response.statusText,
      status_code: response.status,
    }));
    throw error;
  }

  return response.json();
}

// Types
export interface HealthStatus {
  status: string;
  db: string;
  version: string;
}

export interface GlobalStats {
  total_shipments: number;
  total_buyers: number;
  total_suppliers: number;
  total_countries: number;
  total_hs_codes: number;
  ledger_date_range?: { min: string; max: string };
  last_pipeline_runs: Array<{
    pipeline_name: string;
    last_run_at: string;
    status: string;
    rows_processed: number;
  }>;
}

export interface BuyerSummary {
  buyer_uuid: string;
  buyer_name: string;
  buyer_country: string | null;
  buyer_classification: string | null;
  total_shipments: number;
  total_value_usd: number | null;
  current_risk_level: string;
  current_risk_score: number | null;
  has_ghost_flag: boolean;
  first_shipment_date: string | null;
  last_shipment_date: string | null;
}

export interface BuyerListResponse {
  items: BuyerSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface HsCodeSummary {
  hs_code_6: string;
  value_usd: number | null;
  share_pct: number | null;
}

export interface CountrySummary {
  country: string;
  value_usd: number | null;
  share_pct: number | null;
}

export interface Buyer360 {
  buyer_uuid: string;
  buyer_name: string;
  buyer_country: string | null;
  buyer_classification: string | null;
  total_shipments: number;
  total_value_usd: number | null;
  total_qty_kg: number | null;
  total_teu: number | null;
  first_shipment_date: string | null;
  last_shipment_date: string | null;
  active_years: number;
  unique_hs_codes: number;
  unique_origin_countries: number;
  unique_suppliers: number;
  top_hs_codes: HsCodeSummary[];
  top_origin_countries: CountrySummary[];
  current_risk_level: string;
  current_risk_score: number | null;
  current_confidence_score: number | null;
  current_main_reason_code: string | null;
  has_ghost_flag: boolean;
  risk_engine_version: string | null;
}

export interface HsDashboardResponse {
  hs_code_6: string;
  reporting_country: string | null;
  direction: string | null;
  total_shipments: number;
  total_value_usd: number | null;
  total_qty_kg: number | null;
  avg_price_usd_per_kg: number | null;
  unique_buyers: number;
  unique_suppliers: number;
  high_risk_shipments: number;
  high_risk_pct: number | null;
  monthly_data: Array<{
    year: number;
    month: number;
    shipment_count: number;
    total_value_usd: number | null;
  }>;
  monthly_trend: Array<{
    year: number;
    month: number;
    shipment_count: number;
    total_value_usd: number | null;
  }>;
}

export interface TopHsCode {
  hs_code_6: string;
  total_shipments: number;
  total_value_usd: number | null;
  total_qty_kg: number | null;
  high_risk_shipments: number;
  country_count: number;
}

export interface RiskShipment {
  entity_id: string;
  risk_score: number;
  risk_level: string;
  main_reason_code: string;
  hs_code_6: string | null;
  origin_country: string | null;
  destination_country: string | null;
  customs_value_usd: number | null;
  shipment_date: string | null;
}

export interface RiskBuyer {
  entity_id: string;
  buyer_name: string | null;
  buyer_country: string | null;
  risk_score: number;
  risk_level: string;
  main_reason_code: string;
  total_value_usd: number | null;
  total_shipments: number | null;
}

export interface RiskSummary {
  SHIPMENT: Record<string, number>;
  BUYER: Record<string, number>;
  totals: { SHIPMENT: number; BUYER: number };
}

export interface AIStatus {
  available: boolean;
  provider: string | null;
  model: string | null;
  message: string;
}

export interface AIExplanation {
  explanation: string;
  provider: string | null;
  model: string | null;
}

// Buyer Hunter Types
export interface BuyerHunterResult {
  buyer_uuid: string;
  buyer_name: string;
  buyer_country: string | null;
  destination_country: string | null;
  total_value_usd_12m: number;
  total_shipments_12m: number;
  avg_shipment_value_usd: number;
  hs_share_pct: number;
  months_with_shipments_12m: number;
  years_active: number;
  classification: string;
  website_present: boolean;
  website_url: string | null;
  current_risk_level: string;
  risk_score: number | null;
  opportunity_score: number;
  volume_score: number;
  stability_score: number;
  hs_focus_score: number;
  risk_score_component: number;
  data_quality_score: number;
}

export interface BuyerHunterParams {
  hs_code_6: string;
  destination_countries?: string;
  months_lookback?: number;
  min_total_value_usd?: number;
  max_risk_level?: string;
  limit?: number;
}

export interface BuyerHunterTopResponse {
  items: BuyerHunterResult[];
  count: number;
  hs_code_6: string;
  destination_countries: string[] | null;
  months_lookback: number;
  max_risk_level: string;
}

export interface BuyerHunterSearchResponse {
  items: BuyerHunterResult[];
  total: number;
  limit: number;
  offset: number;
  hs_code_6: string;
  destination_countries: string[] | null;
  months_lookback: number;
  min_total_value_usd: number;
  max_risk_level: string;
}

// API Functions
// Admin Upload Types
export interface ValidationResult {
  config_used: string | null;
  required_columns_found: string[];
  required_columns_missing: string[];
  status: string;
}

export interface PipelineResult {
  processing_mode: string;
  run_now: boolean;
  pipeline_run_id: string | null;
  status: string;
}

export interface UploadResponse {
  file_id: number;
  file_name: string;
  file_path: string;
  file_size_bytes: number;
  reporting_country: string;
  direction: string;
  source_format: string;
  min_shipment_date: string | null;  // Populated after standardization
  max_shipment_date: string | null;  // Populated after standardization
  validation: ValidationResult;
  pipeline: PipelineResult;
  created_at: string;
}

export interface FileEntry {
  file_id: number;
  file_name: string;
  file_path: string;
  file_size_bytes: number | null;
  reporting_country: string | null;
  direction: string | null;
  source_format: string | null;
  min_shipment_date: string | null;  // From actual data
  max_shipment_date: string | null;  // From actual data
  status: string;
  created_at: string;
  ingestion_completed_at: string | null;
  standardization_completed_at: string | null;
  identity_completed_at: string | null;
  ledger_completed_at: string | null;
  processing_mode: string | null;
  config_file_used: string | null;
  is_production: boolean | null;
  tags: string | null;
  notes: string | null;
}

export interface FileListResponse {
  items: FileEntry[];
  total: number;
  limit: number;
  offset: number;
}

// EPIC 10: Mapping Registry Types
export type MappingStatus = 'LIVE' | 'VERIFIED' | 'DRAFT' | 'NOT_FOUND';

export interface MappingStatusResponse {
  reporting_country: string;
  direction: string;
  source_format: string;
  status: MappingStatus;
  config_key: string | null;
  yaml_path: string | null;
  last_verified_at: string | null;
  allowed_modes: string[];
  message: string;
}

export const api = {
  // Health & Meta
  getHealth: () => fetchApi<HealthStatus>('/health'),
  getStats: () => fetchApi<GlobalStats>('/meta/stats'),

  // Buyers
  getBuyers: (params: {
    country?: string;
    risk_level?: string;
    hs_code_6?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params.country) searchParams.set('country', params.country);
    if (params.risk_level) searchParams.set('risk_level', params.risk_level);
    if (params.hs_code_6) searchParams.set('hs_code_6', params.hs_code_6);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());
    return fetchApi<BuyerListResponse>(`/buyers?${searchParams}`);
  },

  getBuyer360: (buyerUuid: string) =>
    fetchApi<Buyer360>(`/buyers/${buyerUuid}/360`),

  // HS Dashboard
  getHsDashboard: (params: {
    hs_code_6: string;
    reporting_country?: string;
    direction?: string;
  }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('hs_code_6', params.hs_code_6);
    if (params.reporting_country) searchParams.set('reporting_country', params.reporting_country);
    if (params.direction) searchParams.set('direction', params.direction);
    return fetchApi<HsDashboardResponse>(`/hs-dashboard?${searchParams}`);
  },

  getTopHsCodes: (params?: { reporting_country?: string; direction?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.reporting_country) searchParams.set('reporting_country', params.reporting_country);
    if (params?.direction) searchParams.set('direction', params.direction);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    return fetchApi<{ items: TopHsCode[]; count: number }>(`/hs-dashboard/top-hs-codes?${searchParams}`);
  },

  // Risk
  getRiskShipments: (params?: { level?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.level) searchParams.set('level', params.level);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    return fetchApi<{ items: RiskShipment[]; total: number; limit: number; offset: number }>(
      `/risk/top-shipments?${searchParams}`
    );
  },

  getRiskBuyers: (params?: { level?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.level) searchParams.set('level', params.level);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    return fetchApi<{ items: RiskBuyer[]; total: number; limit: number; offset: number }>(
      `/risk/top-buyers?${searchParams}`
    );
  },

  getRiskSummary: () => fetchApi<RiskSummary>('/risk/summary'),

  // AI Co-Pilot
  getAIStatus: () => fetchApi<AIStatus>('/ai/status'),

  explainBuyer: (buyerUuid: string, useCase: string = 'sales') =>
    fetchApi<AIExplanation>(`/ai/explain-buyer/${buyerUuid}?use_case=${useCase}`, {
      method: 'POST',
    }),

  askAboutBuyer: (buyerUuid: string, question: string) =>
    fetchApi<AIExplanation>(`/ai/ask-buyer/${buyerUuid}`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),

  // Buyer Hunter
  getBuyerHunterTop: (params: BuyerHunterParams) => {
    const searchParams = new URLSearchParams();
    searchParams.set('hs_code_6', params.hs_code_6);
    if (params.destination_countries) searchParams.set('destination_countries', params.destination_countries);
    if (params.months_lookback) searchParams.set('months_lookback', params.months_lookback.toString());
    if (params.min_total_value_usd) searchParams.set('min_total_value_usd', params.min_total_value_usd.toString());
    if (params.max_risk_level) searchParams.set('max_risk_level', params.max_risk_level);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    return fetchApi<BuyerHunterTopResponse>(`/buyer-hunter/top?${searchParams}`);
  },

  getBuyerHunterSearch: (params: BuyerHunterParams & { offset?: number }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('hs_code_6', params.hs_code_6);
    if (params.destination_countries) searchParams.set('destination_countries', params.destination_countries);
    if (params.months_lookback) searchParams.set('months_lookback', params.months_lookback.toString());
    if (params.min_total_value_usd) searchParams.set('min_total_value_usd', params.min_total_value_usd.toString());
    if (params.max_risk_level) searchParams.set('max_risk_level', params.max_risk_level);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());
    return fetchApi<BuyerHunterSearchResponse>(`/buyer-hunter/search?${searchParams}`);
  },

  searchBuyerHunterByName: (params: BuyerHunterParams & { buyer_name: string; offset?: number }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('buyer_name', params.buyer_name);
    searchParams.set('hs_code_6', params.hs_code_6);
    if (params.destination_countries) searchParams.set('destination_countries', params.destination_countries);
    if (params.months_lookback) searchParams.set('months_lookback', params.months_lookback.toString());
    if (params.min_total_value_usd) searchParams.set('min_total_value_usd', params.min_total_value_usd.toString());
    if (params.max_risk_level) searchParams.set('max_risk_level', params.max_risk_level);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());
    return fetchApi<BuyerHunterSearchResponse>(`/buyer-hunter/search-by-name?${searchParams}`);
  },

  // Admin Upload
  getMappingStatus: (params: {
    reporting_country: string;
    direction: string;
    source_format: string;
  }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('reporting_country', params.reporting_country);
    searchParams.set('direction', params.direction);
    searchParams.set('source_format', params.source_format);
    return fetchApi<MappingStatusResponse>(`/admin/mapping-status?${searchParams}`);
  },

  uploadPortDataFile: async (formData: FormData): Promise<UploadResponse> => {
    const response = await fetch(`${API_BASE}/admin/upload-port-file`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary for multipart
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw { error: 'Upload failed', detail: error.detail, status_code: response.status };
    }

    return response.json();
  },

  getUploadedFiles: (params?: {
    limit?: number;
    offset?: number;
    reporting_country?: string;
    direction?: string;
    status?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    if (params?.reporting_country) searchParams.set('reporting_country', params.reporting_country);
    if (params?.direction) searchParams.set('direction', params.direction);
    if (params?.status) searchParams.set('status', params.status);
    return fetchApi<FileListResponse>(`/admin/files?${searchParams}`);
  },

  getAvailableConfigs: () => fetchApi<string[]>('/admin/configs'),
};
