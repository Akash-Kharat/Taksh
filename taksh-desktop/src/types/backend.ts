export interface HealthResponse {
  status: string;
  components: Record<string, string>;
}

export interface MetricsResponse {
  conversation_count: number;
  turn_count: number;
  provider_requests: number;
  provider_failures: number;
  tool_executions: number;
  memory_recalls: number;
  knowledge_searches: number;
  average_latency_ms: number;
  active_sessions: number;
}

export interface ProviderConfigSchema {
  llm: string;
  stt: string;
  tts: string;
  realtime: string;
}

export interface SystemConfigResponse {
  version: string;
  environment: string;
  providers: ProviderConfigSchema;
  api_v1_prefix: string;
  host: string;
  port: number;
  log_level: string;
  enable_provider_health_checks: boolean;
  max_prompt_chars: number;
  max_knowledge_chunks: number;
  max_memory_items: number;
  max_episodes: number;
  health_check_timeout_seconds: number;
}

export interface SystemInfoResponse {
  version: string;
  uptime_seconds: number;
  active_runtime_sessions: number;
  active_voice_sessions: number;
  active_provider_sessions: number;
  memory_episodes: number;
  open_tasks: number;
  metrics_snapshots: number;
  health: string;
}

export interface ReadinessResponse {
  status: 'ready' | 'degraded' | 'not_ready';
  score: number;
  checks_passed: number;
  checks_failed: number;
  warnings: number;
}

export interface ReleaseManifestResponse {
  version: string;
  release_type?: string | null;
  schema_version: string;
  build_date: string;
  completed_milestones?: string[] | null;
  milestones_completed?: string[] | null;
}

export interface ProviderInfoResponse {
  active_provider: string;
  provider_state: string;
  healthy: boolean;
  fallback_active: boolean;
  active_sessions: number;
  reconnect_count: number;
  failure_count: number;
}
