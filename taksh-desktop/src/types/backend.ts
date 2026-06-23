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

export interface ConversationStartResponse {
  runtime_session_id: string;
  voice_session_id: string;
  conversation_state: string;
  conversation_session_state: string;
}

export interface ConversationTurnSchema {
  turn_id: string;
  runtime_session_id: string;
  voice_session_id?: string | null;
  user_text: string;
  assistant_text: string;
  prompt_hash?: string | null;
  provider_name?: string | null;
  latency_ms: number;
  started_at: string;
  completed_at: string;
  cognitive_trace_id?: string | null;
  ai_response_id?: string | null;
  segment_count: number;
  response_truncated: boolean;
  message_version: number;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  memory_hits?: number | null;
  knowledge_hits?: number | null;
}

export interface ConversationMetricsSchema {
  metrics_id: string;
  runtime_session_id: string;
  total_turns: number;
  average_turn_latency_ms: number;
  average_stt_latency_ms: number;
  average_llm_latency_ms: number;
  average_tts_latency_ms: number;
  total_interruptions: number;
  playback_dropped_chunks: number;
}

export interface ConversationSessionDetailResponse {
  turns: ConversationTurnSchema[];
  metrics: ConversationMetricsSchema | null;
  provider_info: Record<string, any> | null;
  interruptions: number;
  session_summary: string | null;
}

export interface ConversationSessionResponse {
  runtime_session_id: string;
  conversation_title?: string | null;
  conversation_session_state: string;
  started_at: string;
  ended_at?: string | null;
  last_message?: string | null;
}

export interface PaginatedConversationSessionsResponse {
  items: ConversationSessionResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConversationInfoResponse {
  profiles: number;
  preferences: number;
  projects: number;
  snapshots: number;
  active_project?: string | null;
  active_sessions: number;
  total_turns: number;
  avg_turn_latency_ms: number;
  avg_stt_latency_ms: number;
  avg_llm_latency_ms: number;
  avg_tts_latency_ms: number;
  provider_fallbacks: number;
  playback_queue_depth: number;
}

export interface ChatGenerateResponse {
  response_id: string;
  trace_id: string;
  content: string;
  provider: string;
  model_name: string;
  status: string;
  latency_ms: number;
}
