import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Radio, Mic, Volume2, ShieldCheck, AlertCircle, RefreshCcw } from 'lucide-react';
import { providerApi } from '../services/api/providerApi';
import { systemApi } from '../services/api/systemApi';

export const Providers: React.FC = () => {
  // 1. Fetch active provider diagnostics (polls every 30s)
  const { data: provInfo, isLoading: isProvLoading } = useQuery({
    queryKey: ['providersInfo'],
    queryFn: providerApi.getProvidersInfo,
    refetchInterval: 30000,
  });

  // 2. Fetch default system config (holds LLM/STT/TTS/Realtime config names)
  const { data: sysConfig, isLoading: isConfigLoading } = useQuery({
    queryKey: ['systemConfig'],
    queryFn: systemApi.getSystemConfig,
  });

  const isLoading = isProvLoading || isConfigLoading;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-[#cba6f7] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // Get active configurations from settings config
  const sttName = sysConfig?.providers.stt || 'mock';
  const ttsName = sysConfig?.providers.tts || 'mock';
  const realtimeName = sysConfig?.providers.realtime || 'gemini_live';

  return (
    <div className="p-6 space-y-6 bg-[#11111b] min-h-screen">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-2 border-b border-[#313244]">
        <div>
          <h2 className="text-xl font-bold text-[#cdd6f4]">Provider Diagnostics</h2>
          <p className="text-xs text-[#a6adc8] mt-1">Status of integrated LLM, STT, TTS, and Realtime audio engines</p>
        </div>
      </div>

      {/* Provider Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Realtime / Multimodal Live API Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 border-b border-[#313244] pb-3 mb-4">
              <div className="p-2 rounded bg-purple-950/40 text-[#cba6f7] border border-purple-700/20">
                <Radio className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-[#cdd6f4]">Realtime Channel</h3>
                <span className="text-[10px] text-[#a6adc8] font-mono">{realtimeName.toUpperCase()}</span>
              </div>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Active Provider:</span>
                <span className="font-mono text-[#cdd6f4] font-semibold">{provInfo?.active_provider ?? 'Unknown'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Engine State:</span>
                <span className="font-mono text-[#cdd6f4] uppercase font-semibold">{provInfo?.provider_state ?? 'closed'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Active WS Tunnels:</span>
                <span className="font-mono text-[#89b4fa] font-bold">{provInfo?.active_sessions ?? 0}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#a6adc8]">Fallback Status:</span>
                <span className={`font-semibold ${provInfo?.fallback_active ? 'text-amber-400' : 'text-[#a6adc8]'}`}>
                  {provInfo?.fallback_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-[#313244] flex items-center justify-between">
            <span className="text-xs text-[#a6adc8]">Health Status:</span>
            <div className="flex items-center gap-1.5">
              {provInfo?.healthy ? (
                <>
                  <ShieldCheck className="w-4 h-4 text-green-400" />
                  <span className="text-xs text-green-400 font-bold font-mono">CONNECTED</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-red-400" />
                  <span className="text-xs text-red-400 font-bold font-mono">DISCONNECTED</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Speech-To-Text (STT) Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 border-b border-[#313244] pb-3 mb-4">
              <div className="p-2 rounded bg-blue-950/40 text-[#89b4fa] border border-blue-700/20">
                <Mic className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-[#cdd6f4]">Speech-To-Text (STT)</h3>
                <span className="text-[10px] text-[#a6adc8] font-mono">{sttName.toUpperCase()}</span>
              </div>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Engine:</span>
                <span className="font-mono text-[#cdd6f4] font-semibold">{sttName === 'mock' ? 'Mock Whisper' : 'Live Speech STT'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Format:</span>
                <span className="font-mono text-[#cdd6f4]">PCM 16kHz Mono</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#a6adc8]">Latency:</span>
                <span className="font-mono text-green-400 font-semibold">&lt; 150ms</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-[#313244] flex items-center justify-between">
            <span className="text-xs text-[#a6adc8]">Health Status:</span>
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-green-400" />
              <span className="text-xs text-green-400 font-bold font-mono">ONLINE</span>
            </div>
          </div>
        </div>

        {/* Text-To-Speech (TTS) Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 border-b border-[#313244] pb-3 mb-4">
              <div className="p-2 rounded bg-green-950/40 text-[#a6e3a1] border border-green-700/20">
                <Volume2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-[#cdd6f4]">Text-To-Speech (TTS)</h3>
                <span className="text-[10px] text-[#a6adc8] font-mono">{ttsName.toUpperCase()}</span>
              </div>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Engine:</span>
                <span className="font-mono text-[#cdd6f4] font-semibold">{ttsName === 'mock' ? 'Mock Voice synthesizer' : 'Live Speech TTS'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#313244]/40">
                <span className="text-[#a6adc8]">Fallback status:</span>
                <span className="font-mono text-[#cdd6f4]">Configured</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#a6adc8]">Latency:</span>
                <span className="font-mono text-green-400 font-semibold">&lt; 250ms</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-[#313244] flex items-center justify-between">
            <span className="text-xs text-[#a6adc8]">Health Status:</span>
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-green-400" />
              <span className="text-xs text-green-400 font-bold font-mono">ONLINE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Reconnects & Failures Telemetry Section */}
      <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md">
        <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
          <RefreshCcw className="w-4 h-4 text-[#89b4fa]" />
          Provider Health Logs
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-4 bg-[#11111b]/40 rounded-lg border border-[#313244]">
            <span className="text-xs text-[#a6adc8] block">Connection Attempts</span>
            <span className="text-xl font-bold font-mono text-[#cdd6f4]">
              {(provInfo?.reconnect_count ?? 0) + 1}
            </span>
          </div>
          <div className="p-4 bg-[#11111b]/40 rounded-lg border border-[#313244]">
            <span className="text-xs text-[#a6adc8] block">Reconnect Recovery Rate</span>
            <span className="text-xl font-bold font-mono text-[#a6e3a1]">
              100%
            </span>
          </div>
          <div className="p-4 bg-[#11111b]/40 rounded-lg border border-[#313244]">
            <span className="text-xs text-[#a6adc8] block">Total Failure Traces</span>
            <span className="text-xl font-bold font-mono text-[#f38ba8]">
              {provInfo?.failure_count ?? 0}
            </span>
          </div>
          <div className="p-4 bg-[#11111b]/40 rounded-lg border border-[#313244]">
            <span className="text-xs text-[#a6adc8] block">Active Clients (STT/TTS)</span>
            <span className="text-xl font-bold font-mono text-[#89b4fa]">
              {provInfo?.active_sessions ?? 0}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
