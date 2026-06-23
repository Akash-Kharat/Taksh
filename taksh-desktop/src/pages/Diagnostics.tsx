import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Download,
  Activity,
  Percent,
  CheckCircle,
  HelpCircle,
  XCircle,
  TrendingUp,
  Cpu
} from 'lucide-react';
import { systemApi } from '../services/api/systemApi';
import { healthApi } from '../services/api/healthApi';
import { providerApi } from '../services/api/providerApi';

export const Diagnostics: React.FC = () => {
  const queryClient = useQueryClient();

  // 1. Fetch metrics (polls every 15s)
  const { data: metrics, isLoading: isMetricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: systemApi.getMetrics,
    refetchInterval: 15000,
  });

  // 2. Fetch health checks (polls every 15s)
  const { data: health, isLoading: isHealthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.getHealth,
    refetchInterval: 15000,
  });

  // Export Diagnostics handler (satisfies Revision 4)
  const handleExport = async () => {
    try {
      // Pull latest cached values or fetch directly if needed
      const sysInfo = await queryClient.ensureQueryData({
        queryKey: ['systemInfo'],
        queryFn: systemApi.getSystemInfo,
      });

      const readiness = await queryClient.ensureQueryData({
        queryKey: ['readiness'],
        queryFn: systemApi.getReadiness,
      });

      const providers = await queryClient.ensureQueryData({
        queryKey: ['providersInfo'],
        queryFn: providerApi.getProvidersInfo,
      });

      const exportData = {
        system_info: sysInfo || {},
        health: health || {},
        providers: providers || {},
        readiness: readiness || {},
        metrics: metrics || {},
        timestamp: new Date().toISOString(),
      };

      // Trigger JSON file download
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'taksh-diagnostics.json';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export diagnostics:', err);
      alert('Failed to compile diagnostics export.');
    }
  };

  const isLoading = isMetricsLoading || isHealthLoading;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-[#cba6f7] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-[#11111b] min-h-screen">
      {/* Header with Export Button */}
      <div className="flex justify-between items-center pb-2 border-b border-[#313244]">
        <div>
          <h2 className="text-xl font-bold text-[#cdd6f4]">System Diagnostics</h2>
          <p className="text-xs text-[#a6adc8] mt-1">Granular telemetry metrics and component health validation</p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-[#a6e3a1] hover:bg-[#94e2d5] text-[#11111b] font-semibold text-xs rounded-lg shadow transition-all duration-200"
        >
          <Download className="w-3.5 h-3.5" />
          Export Diagnostics
        </button>
      </div>

      {/* Grid: Metrics Overview & Subsystem Statuses */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Latency Stats Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div className="space-y-1">
            <span className="text-xs text-[#a6adc8] font-semibold uppercase tracking-wider block">Average Latency</span>
            <span className="text-3xl font-extrabold font-mono text-[#89b4fa]">
              {metrics?.average_latency_ms ? `${metrics.average_latency_ms.toFixed(1)}ms` : '0.0ms'}
            </span>
          </div>
          <div className="text-[10px] text-[#a6adc8] mt-4 flex items-center gap-1.5 border-t border-[#313244] pt-2">
            <TrendingUp className="w-3.5 h-3.5 text-[#89b4fa]" />
            Response processing time across sessions
          </div>
        </div>

        {/* Turn Rate Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div className="space-y-1">
            <span className="text-xs text-[#a6adc8] font-semibold uppercase tracking-wider block">Total User Turns</span>
            <span className="text-3xl font-extrabold font-mono text-[#cba6f7]">
              {metrics?.turn_count ?? 0}
            </span>
          </div>
          <div className="text-[10px] text-[#a6adc8] mt-4 flex items-center gap-1.5 border-t border-[#313244] pt-2">
            <Activity className="w-3.5 h-3.5 text-[#cba6f7]" />
            Turn count captures user speech instances
          </div>
        </div>

        {/* Failure Rate Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div className="space-y-1">
            <span className="text-xs text-[#a6adc8] font-semibold uppercase tracking-wider block">Provider Failure Rate</span>
            <span className="text-3xl font-extrabold font-mono text-[#f38ba8]">
              {metrics && metrics.provider_requests > 0
                ? `${((metrics.provider_failures / metrics.provider_requests) * 100).toFixed(1)}%`
                : '0.0%'}
            </span>
          </div>
          <div className="text-[10px] text-[#a6adc8] mt-4 flex items-center gap-1.5 border-t border-[#313244] pt-2">
            <Percent className="w-3.5 h-3.5 text-[#f38ba8]" />
            {metrics?.provider_failures ?? 0} failures / {metrics?.provider_requests ?? 0} total requests
          </div>
        </div>
      </div>

      {/* Grid: Detailed Subsystems & System Counters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Telemetry Counter Metrics Table */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md">
          <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#cba6f7]" />
            Telemetry Counter Metrics
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-[#cdd6f4]">
              <thead>
                <tr className="border-b border-[#313244] text-[#a6adc8] text-left uppercase text-[10px] tracking-wider">
                  <th className="pb-2 font-semibold">Telemetry Indicator</th>
                  <th className="pb-2 text-right font-semibold">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#313244]/40 font-mono">
                <tr>
                  <td className="py-2.5 text-[#a6adc8]">Total Conversations</td>
                  <td className="py-2.5 text-right font-semibold">{metrics?.conversation_count ?? 0}</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-[#a6adc8]">Active WebSocket Sessions</td>
                  <td className="py-2.5 text-right font-semibold text-[#89b4fa]">{metrics?.active_sessions ?? 0}</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-[#a6adc8]">Tool Executions</td>
                  <td className="py-2.5 text-right font-semibold">{metrics?.tool_executions ?? 0}</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-[#a6adc8]">Memory Recalls (RAG)</td>
                  <td className="py-2.5 text-right font-semibold text-[#cba6f7]">{metrics?.memory_recalls ?? 0}</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-[#a6adc8]">Knowledge Ingestion Searches</td>
                  <td className="py-2.5 text-right font-semibold">{metrics?.knowledge_searches ?? 0}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Detailed Health Indicator Logs */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md">
          <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#89b4fa]" />
            Component Diagnostics Checks
          </h3>
          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
            {health && health.components ? (
              Object.entries(health.components).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center justify-between p-2 rounded bg-[#11111b]/40 border border-[#313244]"
                >
                  <div className="flex items-center gap-2">
                    {status === 'healthy' ? (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    ) : status === 'degraded' ? (
                      <HelpCircle className="w-4 h-4 text-amber-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className="text-xs font-semibold capitalize text-[#cdd6f4]">{name} check</span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                      status === 'healthy'
                        ? 'bg-green-950/30 text-green-400 border border-green-700/30'
                        : status === 'degraded'
                        ? 'bg-amber-950/30 text-amber-400 border border-amber-700/30'
                        : 'bg-red-950/30 text-red-400 border border-red-700/30'
                    }`}
                  >
                    {status.toUpperCase()}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#a6adc8]">No active diagnostics check logs found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
