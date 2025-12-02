import { useState, useRef, useMemo, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { 
  Upload, FileSpreadsheet, CheckCircle, AlertCircle, 
  Loader2, Settings, Play, Clock, Info, Shield
} from 'lucide-react';
import { api, UploadResponse, FileListResponse, ApiError, MappingStatusResponse } from '../api/client';

// Constants
// Common countries for quick selection - user can also type any custom country
const COMMON_COUNTRIES = [
  'INDIA', 'KENYA', 'INDONESIA', 'CHINA', 'USA', 'UAE', 'UK', 'GERMANY',
  'MALAYSIA', 'VIETNAM', 'THAILAND', 'SINGAPORE', 'JAPAN', 'SOUTH KOREA',
  'SAUDI ARABIA', 'BRAZIL', 'MEXICO', 'CANADA', 'AUSTRALIA', 'FRANCE',
  'ITALY', 'SPAIN', 'NETHERLANDS', 'BELGIUM', 'TURKEY', 'EGYPT', 'SOUTH AFRICA',
  'NIGERIA', 'BANGLADESH', 'PAKISTAN', 'SRI LANKA', 'PHILIPPINES', 'TAIWAN'
];
const DIRECTIONS = ['IMPORT', 'EXPORT'];
const SOURCE_FORMATS = ['FULL', 'SHORT', 'OTHER'];
const DATA_GRAINS = ['SHIPMENT_LINE', 'CONTAINER', 'INVOICE', 'UNKNOWN'];
const DATA_QUALITY_LEVELS = ['RAW', 'CLEANED_BASIC', 'CLEANED_AAZIKO', 'UNKNOWN'];
const PROCESSING_MODES = [
  { value: 'INGEST_ONLY', label: 'Ingest Only', description: 'Save file to registry only' },
  { value: 'INGEST_AND_STANDARDIZE', label: 'Ingest + Standardize', description: 'Run standardization after ingestion' },
  { value: 'FULL_PIPELINE', label: 'Full Pipeline', description: 'Run complete ETL pipeline' },
];
// Note: Year and Month are no longer required - they are derived from the date column in the data

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString();
}

export default function AdminUpload() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [reportingCountry, setReportingCountry] = useState('KENYA');
  const [countryInputValue, setCountryInputValue] = useState('KENYA');
  const [showCountrySuggestions, setShowCountrySuggestions] = useState(false);
  
  // Filter country suggestions based on input
  const filteredCountries = useMemo(() => {
    if (!countryInputValue.trim()) return COMMON_COUNTRIES;
    const search = countryInputValue.toUpperCase().trim();
    return COMMON_COUNTRIES.filter(c => c.includes(search));
  }, [countryInputValue]);
  const [direction, setDirection] = useState('IMPORT');
  const [sourceFormat, setSourceFormat] = useState('FULL');
  const [sourceProvider, setSourceProvider] = useState('');
  const [dataGrain, setDataGrain] = useState('');
  const [isProduction, setIsProduction] = useState(true);
  const [dataQualityLevel, setDataQualityLevel] = useState('RAW');
  const [tags, setTags] = useState('');
  const [notes, setNotes] = useState('');
  const [headerRowIndex, setHeaderRowIndex] = useState(1);
  const [sheetName, setSheetName] = useState('');
  const [processingMode, setProcessingMode] = useState('INGEST_ONLY');
  const [runNow, setRunNow] = useState(false);
  
  // Success/Error state
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  // Show advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Recent files query
  const { data: recentFiles, refetch: refetchFiles } = useQuery<FileListResponse>({
    queryKey: ['admin-files'],
    queryFn: () => api.getUploadedFiles({ limit: 10 }),
  });
  
  // EPIC 10: Mapping status query
  const { data: mappingStatus, isLoading: mappingStatusLoading } = useQuery<MappingStatusResponse>({
    queryKey: ['mapping-status', reportingCountry, direction, sourceFormat],
    queryFn: () => api.getMappingStatus({
      reporting_country: reportingCountry,
      direction: direction,
      source_format: sourceFormat,
    }),
    enabled: !!reportingCountry && !!direction && !!sourceFormat,
  });
  
  // Reset processing mode if current selection is not allowed
  useEffect(() => {
    if (mappingStatus && !mappingStatus.allowed_modes.includes(processingMode)) {
      setProcessingMode(mappingStatus.allowed_modes[0] || 'INGEST_ONLY');
    }
  }, [mappingStatus, processingMode]);
  
  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return api.uploadPortDataFile(formData);
    },
    onSuccess: (data) => {
      setUploadResult(data);
      setUploadError(null);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      refetchFiles();
    },
    onError: (error: ApiError) => {
      setUploadError(error.detail || 'Upload failed');
      setUploadResult(null);
    },
  });
  
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!['xlsx', 'xls', 'csv'].includes(ext || '')) {
        setUploadError('Invalid file type. Please upload .xlsx, .xls, or .csv files.');
        return;
      }
      setSelectedFile(file);
      setUploadError(null);
      setUploadResult(null);
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setUploadError('Please select a file to upload');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('reporting_country', reportingCountry);
    formData.append('direction', direction);
    formData.append('source_format', sourceFormat);
    formData.append('is_production', isProduction.toString());
    formData.append('processing_mode', processingMode);
    formData.append('run_now', runNow.toString());
    formData.append('header_row_index', headerRowIndex.toString());
    
    if (sourceProvider) formData.append('source_provider', sourceProvider);
    if (dataGrain) formData.append('data_grain', dataGrain);
    if (dataQualityLevel) formData.append('data_quality_level', dataQualityLevel);
    if (tags) formData.append('tags', tags);
    if (notes) formData.append('notes', notes);
    if (sheetName) formData.append('sheet_name', sheetName);
    
    uploadMutation.mutate(formData);
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Port Data File</h1>
        <p className="text-gray-500 mt-1">
          Upload Excel or CSV files with trade data for processing
        </p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Form */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200">
            {/* File Selection */}
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-blue-600" />
                File Selection
              </h2>
              
              <div 
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                  ${selectedFile ? 'border-green-300 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'}`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                
                {selectedFile ? (
                  <div className="flex items-center justify-center gap-3">
                    <CheckCircle className="h-8 w-8 text-green-500" />
                    <div className="text-left">
                      <p className="font-medium text-gray-900">{selectedFile.name}</p>
                      <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600">Click to select or drag and drop</p>
                    <p className="text-sm text-gray-400 mt-1">Accepts .xlsx, .xls, .csv</p>
                  </>
                )}
              </div>
            </div>
            
            {/* Trade Context */}
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Trade Context</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="relative">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Reporting Country *
                  </label>
                  <input
                    type="text"
                    value={countryInputValue}
                    onChange={(e) => {
                      const val = e.target.value.toUpperCase();
                      setCountryInputValue(val);
                      setReportingCountry(val);
                      setShowCountrySuggestions(true);
                    }}
                    onFocus={() => setShowCountrySuggestions(true)}
                    onBlur={() => {
                      // Delay hide to allow click on suggestions
                      setTimeout(() => setShowCountrySuggestions(false), 200);
                    }}
                    placeholder="Type or select country..."
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  {showCountrySuggestions && filteredCountries.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                      {filteredCountries.slice(0, 10).map(country => (
                        <button
                          key={country}
                          type="button"
                          className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            setCountryInputValue(country);
                            setReportingCountry(country);
                            setShowCountrySuggestions(false);
                          }}
                        >
                          {country}
                        </button>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Type any country name (e.g., MALAYSIA, VIETNAM)
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Direction *
                  </label>
                  <select
                    value={direction}
                    onChange={(e) => setDirection(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {DIRECTIONS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source Format *
                  </label>
                  <select
                    value={sourceFormat}
                    onChange={(e) => setSourceFormat(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {SOURCE_FORMATS.map(f => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </div>
                
                {/* Note: Year and Month are automatically derived from date columns in the data */}
                <div className="col-span-2 md:col-span-3">
                  <p className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
                    📅 Year and month will be automatically extracted from the date column in your data file.
                  </p>
                </div>
                
                {/* EPIC 10: Mapping Status Pill */}
                <div className="col-span-2 md:col-span-3">
                  {mappingStatusLoading ? (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Checking mapping status...
                    </div>
                  ) : mappingStatus && (
                    <div className={`flex items-center gap-2 p-3 rounded-lg border ${
                      mappingStatus.status === 'LIVE' 
                        ? 'bg-green-50 border-green-200 text-green-800'
                        : mappingStatus.status === 'VERIFIED'
                        ? 'bg-yellow-50 border-yellow-200 text-yellow-800'
                        : 'bg-red-50 border-red-200 text-red-800'
                    }`}>
                      <Shield className="h-5 w-5" />
                      <div className="flex-1">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          mappingStatus.status === 'LIVE'
                            ? 'bg-green-100 text-green-800'
                            : mappingStatus.status === 'VERIFIED'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {mappingStatus.status}
                        </span>
                        <span className="ml-2 text-sm">{mappingStatus.message}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Advanced Options Toggle */}
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
              >
                <Settings className="h-4 w-4" />
                {showAdvanced ? 'Hide' : 'Show'} Advanced Options
              </button>
            </div>
            
            {/* Advanced Options */}
            {showAdvanced && (
              <div className="p-6 border-b border-gray-200 bg-gray-50">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Source Provider
                    </label>
                    <input
                      type="text"
                      value={sourceProvider}
                      onChange={(e) => setSourceProvider(e.target.value)}
                      placeholder="e.g., Eximpedia"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data Grain
                    </label>
                    <select
                      value={dataGrain}
                      onChange={(e) => setDataGrain(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Select...</option>
                      {DATA_GRAINS.map(g => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data Quality Level
                    </label>
                    <select
                      value={dataQualityLevel}
                      onChange={(e) => setDataQualityLevel(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {DATA_QUALITY_LEVELS.map(q => (
                        <option key={q} value={q}>{q}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Header Row Index
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={headerRowIndex}
                      onChange={(e) => setHeaderRowIndex(parseInt(e.target.value))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Sheet Name
                    </label>
                    <input
                      type="text"
                      value={sheetName}
                      onChange={(e) => setSheetName(e.target.value)}
                      placeholder="First sheet if empty"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div className="flex items-center">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isProduction}
                        onChange={(e) => setIsProduction(e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-gray-700">Production Data</span>
                    </label>
                  </div>
                  
                  <div className="col-span-2 md:col-span-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tags (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={tags}
                      onChange={(e) => setTags(e.target.value)}
                      placeholder="e.g., tiles, pilot, kenya-2023"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div className="col-span-2 md:col-span-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Notes
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={2}
                      placeholder="Any additional notes about this file..."
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}
            
            {/* Pipeline Options */}
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Play className="h-5 w-5 text-blue-600" />
                Pipeline Options
              </h2>
              
              <div className="space-y-4">
                <div className="space-y-2">
                  {PROCESSING_MODES.map(mode => {
                    const isAllowed = !mappingStatus || mappingStatus.allowed_modes.includes(mode.value);
                    return (
                      <label 
                        key={mode.value} 
                        className={`flex items-start gap-3 p-3 rounded-lg border ${
                          isAllowed 
                            ? 'cursor-pointer border-gray-200 hover:bg-gray-50' 
                            : 'cursor-not-allowed border-gray-100 bg-gray-50 opacity-50'
                        }`}
                      >
                        <input
                          type="radio"
                          name="processingMode"
                          value={mode.value}
                          checked={processingMode === mode.value}
                          onChange={(e) => setProcessingMode(e.target.value)}
                          disabled={!isAllowed}
                          className="mt-1 w-4 h-4 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <p className={`font-medium ${isAllowed ? 'text-gray-900' : 'text-gray-400'}`}>
                            {mode.label}
                            {!isAllowed && (
                              <span className="ml-2 text-xs text-red-500">
                                (Requires {mode.value === 'FULL_PIPELINE' ? 'LIVE' : 'VERIFIED'} status)
                              </span>
                            )}
                          </p>
                          <p className={`text-sm ${isAllowed ? 'text-gray-500' : 'text-gray-400'}`}>{mode.description}</p>
                        </div>
                      </label>
                    );
                  })}
                </div>
                
                <div className="flex items-center gap-3 pt-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={runNow}
                      onChange={(e) => setRunNow(e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <span className="font-medium text-gray-900">Run Pipeline Now</span>
                  </label>
                  <span className="text-sm text-gray-500">
                    (If unchecked, file will be queued for later processing)
                  </span>
                </div>
              </div>
            </div>
            
            {/* Submit Button & Status */}
            <div className="p-6">
              {uploadError && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800">Upload Failed</p>
                    <p className="text-sm text-red-600">{uploadError}</p>
                  </div>
                </div>
              )}
              
              {uploadResult && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-green-800">Upload Successful!</p>
                    <p className="text-sm text-green-600">
                      File ID: {uploadResult.file_id} | 
                      Status: {uploadResult.pipeline.status}
                      {uploadResult.pipeline.pipeline_run_id && 
                        ` | Pipeline Run: ${uploadResult.pipeline.pipeline_run_id.slice(0, 8)}...`}
                    </p>
                    {uploadResult.validation.config_used && (
                      <p className="text-sm text-green-600">
                        Config: {uploadResult.validation.config_used}
                      </p>
                    )}
                  </div>
                </div>
              )}
              
              <button
                type="submit"
                disabled={!selectedFile || uploadMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="h-5 w-5" />
                    Upload File
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
        
        {/* Recent Uploads Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Clock className="h-5 w-5 text-gray-500" />
                Recent Uploads
              </h2>
            </div>
            
            <div className="divide-y divide-gray-100">
              {recentFiles?.items.length === 0 && (
                <div className="p-4 text-center text-gray-500">
                  <Info className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p>No files uploaded yet</p>
                </div>
              )}
              
              {recentFiles?.items.map(file => (
                <div key={file.file_id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900 truncate text-sm">
                        {file.file_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {file.reporting_country} | {file.direction}
                        {file.min_shipment_date && ` | ${file.min_shipment_date.slice(0, 10)}`}
                        {file.max_shipment_date && file.min_shipment_date !== file.max_shipment_date && ` to ${file.max_shipment_date.slice(0, 10)}`}
                      </p>
                      <p className="text-xs text-gray-400">
                        {formatDate(file.created_at)}
                      </p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full flex-shrink-0
                      ${file.status === 'INGESTED' ? 'bg-green-100 text-green-700' : 
                        file.status === 'FAILED' ? 'bg-red-100 text-red-700' : 
                        'bg-gray-100 text-gray-700'}`}
                    >
                      {file.status}
                    </span>
                  </div>
                  
                  {/* Pipeline Progress */}
                  <div className="mt-2 flex gap-1">
                    <div className={`h-1 flex-1 rounded ${file.ingestion_completed_at ? 'bg-green-400' : 'bg-gray-200'}`} title="Ingestion" />
                    <div className={`h-1 flex-1 rounded ${file.standardization_completed_at ? 'bg-green-400' : 'bg-gray-200'}`} title="Standardization" />
                    <div className={`h-1 flex-1 rounded ${file.identity_completed_at ? 'bg-green-400' : 'bg-gray-200'}`} title="Identity" />
                    <div className={`h-1 flex-1 rounded ${file.ledger_completed_at ? 'bg-green-400' : 'bg-gray-200'}`} title="Ledger" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
