/**
 * ==============================================================================
 * ORCA — Marine Ecosystem Reasoning with Collaborative Agents
 * TypeScript Data Models & Contract Definitions for Frontend / FastAPI Backend
 * ==============================================================================
 */

// ------------------------------------------------------------------------------
// 1. Authentication & Session Types
// ------------------------------------------------------------------------------

export type UserRole = 'researcher' | 'oceanographer' | 'fleet_officer' | 'admin';

export interface UserProfile {
  id: string | number;
  fullName: string;
  email: string;
  role: UserRole;
  affiliation?: string;
  avatarInitials?: string;
  createdAt: string;
}

export interface AuthTokens {
  accessToken: string;
  tokenType: 'Bearer';
  expiresInSeconds: number;
}

export interface AuthResponse {
  user: UserProfile;
  tokens: AuthTokens;
  status: 'authenticated' | 'pending_verification';
}

export interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// ------------------------------------------------------------------------------
// 2. Geospatial & Coordinate Models
// ------------------------------------------------------------------------------

export interface GeoCoordinates {
  latitude: number;
  longitude: number;
  locationName?: string;
}

export interface LocationData {
  location_name: string;
  requested_latitude: number;
  requested_longitude: number;
  grid_latitude?: number | null;
  grid_longitude?: number | null;
}

export interface Waypoint {
  name: string;
  latitude: number;
  longitude: number;
  bearingDeg?: number;
  distanceNm?: number;
}

// ------------------------------------------------------------------------------
// 3. Marine Forecast & Open-Meteo Contract
// ------------------------------------------------------------------------------

export interface TimeSeriesPoint {
  timestamp: string;
  wave_height?: number | null;
  wave_period_s?: number | null;
  wave_direction_deg?: number | null;
  wind_wave_height_m?: number | null;
  swell_wave_height_m?: number | null;
}

export interface MeasurementsData {
  variable: string; // e.g. "wave_height"
  unit: string;     // e.g. "m"
  sample_count: number;
  min_wave_height_m?: number | null;
  max_wave_height_m?: number | null;
  avg_wave_height_m?: number | null;
  latest_wave_height_m?: number | null;
  timeseries: TimeSeriesPoint[];
}

export interface TimestampsData {
  retrieved_at: string;
  forecast_start?: string | null;
  forecast_end?: string | null;
  forecast_time_window_hours: number;
}

export interface SourceData {
  provider: string; // "open-meteo-marine"
  model_timezone: string; // "GMT"
  attribution: string;
  citation: string;
}

export interface ValidationStatusData {
  status: 'valid' | 'insufficient_evidence' | 'evidence_requires_review';
  is_valid: boolean;
  issues: string[];
  quality_flags: string[];
  records_analyzed: number;
}

export interface AnalysisData {
  sea_state_code?: number | null; // WMO Code Table 3700 (0-9)
  sea_state_category: string;     // e.g. "Moderate (1.25 - 2.50 m)"
  rule_standard: string;          // e.g. "WMO Code Table 3700"
  advisory: string;
  generation_mode: 'deterministic' | 'llm';
}

export interface OrcaAnalyzeResponse {
  agent_name: string;
  workflow_id: string;
  status: 'success' | 'insufficient_evidence' | 'error';
  location: LocationData;
  measurements: MeasurementsData;
  units: Record<string, string>;
  timestamps: TimestampsData;
  source: SourceData;
  validation_status: ValidationStatusData;
  analysis: AnalysisData;
  limitations: string[];
  step_progress: string[];
}

// ------------------------------------------------------------------------------
// 4. Five Specialist Agents Contract Models
// ------------------------------------------------------------------------------

export type SpecialistAgentId =
  | 'weather'
  | 'ocean'
  | 'fishing_zone'
  | 'route'
  | 'safety_risk'
  | 'orchestrator'
  | 'assistant';

export interface WeatherObservations {
  temperature_c?: number;
  wind_speed_kmh?: number;
  wind_speed_knots?: number;
  wind_direction_deg?: number;
  beaufort_scale?: {
    force: number;
    description: string;
  };
  precipitation_probability?: number;
}

export interface OceanObservations {
  avg_wave_height_m?: number;
  max_wave_height_m?: number;
  dominant_wave_period_s?: number;
  sea_water_temperature_c?: number;
  sample_count: number;
}

export interface FisheriesObservations {
  thermal_front_score?: number;
  chlorophyll_gradient?: string;
  monsoon_advisory?: string;
  artisanal_vessel_status?: string;
  target_species_viability?: Record<string, string>;
}

export interface RouteObservations {
  origin_name?: string;
  destination_name?: string;
  total_distance_nm?: number;
  total_distance_km?: number;
  initial_bearing_deg?: number;
  estimated_transit_time_hours?: number;
  is_navigable_channel_estimate?: boolean;
}

export interface SafetyRiskObservations {
  overall_hazard_score?: number; // 0.00 to 1.00
  hazard_level?: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  wind_risk_flag?: boolean;
  wave_risk_flag?: boolean;
  monsoon_risk_flag?: boolean;
  advisory_bulletin?: string;
}

// ------------------------------------------------------------------------------
// 5. AI Workspace Assistant & Chat Contract
// ------------------------------------------------------------------------------

export interface ExecutionPlanStep {
  step_id: number;
  description: string;
  tool_name?: string | null;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  result_summary?: string | null;
}

export interface ToolCallRecord {
  call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'denied' | 'waiting_approval';
  output?: unknown;
  error?: string | null;
  duration_ms?: number | null;
  requires_approval?: boolean;
  diff?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agent_type?: SpecialistAgentId | 'auto';
  plan?: ExecutionPlanStep[] | null;
  tool_calls?: ToolCallRecord[] | null;
  agent_results?: Record<string, unknown> | null;
  evidence_summary?: Record<string, unknown> | null;
  limitations?: string[] | null;
}

export interface AssistantChatRequest {
  message: string;
  conversation_id?: string | null;
  agent_id?: SpecialistAgentId | 'auto';
  client_context?: {
    latitude?: number;
    longitude?: number;
    sector?: string;
    vessel_speed_knots?: number;
  } | null;
}

export interface AssistantChatResponse {
  conversation_id: string;
  response_message: ChatMessage;
  plan: ExecutionPlanStep[];
  tool_calls: ToolCallRecord[];
  agent_results: Record<string, unknown>;
  evidence_summary: Record<string, unknown>;
  limitations: string[];
  status: 'completed' | 'waiting_approval' | 'error';
  generated_at: string;
}

// ------------------------------------------------------------------------------
// 6. Mock Data Constants (For Offline Dev / Storybook / Unit Testing)
// ------------------------------------------------------------------------------

export const MOCK_USER: UserProfile = {
  id: 'usr_orca_01',
  fullName: 'Dr. Rachel Carson',
  email: 'rachel.carson@orca-marine.org',
  role: 'oceanographer',
  affiliation: 'National Institute of Oceanography (NIO)',
  avatarInitials: 'RC',
  createdAt: '2026-01-15T08:00:00Z',
};

export const MOCK_ADMIN: UserProfile = {
  id: 'usr_orca_admin',
  fullName: 'Chief Systems Administrator',
  email: 'admin@orca.io',
  role: 'admin',
  affiliation: 'ORCA Maritime Intelligence Operations',
  avatarInitials: 'AD',
  createdAt: '2026-01-01T00:00:00Z',
};

export const MOCK_MARINE_RESPONSE: OrcaAnalyzeResponse = {
  agent_name: 'ORCA Marine Intelligence Agent',
  workflow_id: 'wf_mock_marine_771',
  status: 'success',
  location: {
    location_name: 'Goa Coastal Shelf (Offshore Sector 4)',
    requested_latitude: 15.0,
    requested_longitude: 72.0,
    grid_latitude: 15.0,
    grid_longitude: 72.0,
  },
  measurements: {
    variable: 'wave_height',
    unit: 'meters',
    sample_count: 24,
    min_wave_height_m: 1.1,
    max_wave_height_m: 1.85,
    avg_wave_height_m: 1.42,
    latest_wave_height_m: 1.45,
    timeseries: [
      { timestamp: '2026-10-12T00:00:00Z', wave_height: 1.2 },
      { timestamp: '2026-10-12T06:00:00Z', wave_height: 1.4 },
      { timestamp: '2026-10-12T12:00:00Z', wave_height: 1.55 },
      { timestamp: '2026-10-12T18:00:00Z', wave_height: 1.42 },
    ],
  },
  units: {
    wave_height: 'm',
    wind_speed: 'knots',
    water_temperature: '°C',
    distance: 'NM',
  },
  timestamps: {
    retrieved_at: '2026-10-12T12:00:00Z',
    forecast_start: '2026-10-12T00:00:00Z',
    forecast_end: '2026-10-13T00:00:00Z',
    forecast_time_window_hours: 24,
  },
  source: {
    provider: 'open-meteo-marine',
    model_timezone: 'GMT',
    attribution: 'Open-Meteo Marine Weather API (ECMWF / Meteo-France models)',
    citation: 'WMO Code Table 3700 / Douglas Sea Scale; Open-Meteo API',
  },
  validation_status: {
    status: 'valid',
    is_valid: true,
    issues: [],
    quality_flags: ['ECMWF_ENS_CONSISTENT', 'BUOY_GROUNDED'],
    records_analyzed: 24,
  },
  analysis: {
    sea_state_code: 3,
    sea_state_category: 'Slight / Moderate (1.25 - 2.50 m)',
    rule_standard: 'WMO Code Table 3700',
    advisory: 'Conditions are favorable for commercial navigation. Small artisanal craft should exercise caution during tidal ebbs.',
    generation_mode: 'deterministic',
  },
  limitations: [
    'Observation models reflect open shelf bathymetry; shallow tidal estuaries may exhibit increased wave shoaling.',
  ],
  step_progress: [
    'Fetch ECMWF marine wave grids',
    'Execute Douglas / WMO 3700 state classification',
    'Validate evidence against coastal bounding boxes',
  ],
};
