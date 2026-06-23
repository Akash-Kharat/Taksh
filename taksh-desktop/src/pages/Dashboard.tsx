import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldCheck,
  Server,
  Database,
  Cpu,
  Milestone,
  CheckCircle,
  XCircle,
  HelpCircle
} from 'lucide-react';
import { systemApi } from '../services/api/systemApi';
import { healthApi } from '../services/api/healthApi';

export const Dashboard: React.FC = () => {
  // 1. Fetch system info (polls every 15s)
  const { data: sysInfo, isLoading: isSysLoading } = useQuery({
    queryKey: ['systemInfo'],
    queryFn: systemApi.getSystemInfo,
    refetchInterval: 15000,
  });

  // 2. Fetch readiness report (polls every 15s)
  const { data: readiness, isLoading: isReadinessLoading } = useQuery({
    queryKey: ['readiness'],
    queryFn: systemApi.getReadiness,
    refetchInterval: 15000,
  });

  // 3. Fetch health report (polls every 15s)
  const { data: health, isLoading: isHealthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.getHealth,
    refetchInterval: 15000,
  });

  // 4. Fetch release metadata (doesn't require aggressive polling)
  const { data: release, isLoading: isReleaseLoading } = useQuery({
    queryKey: ['release'],
    queryFn: systemApi.getReleaseInfo,
  });

  const isLoading = isSysLoading || isReadinessLoading || isHealthLoading || isReleaseLoading;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-[#cba6f7] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // Format uptime: e.g., 2h 45m 12s
  const formatUptime = (seconds?: number): string => {
    if (seconds === undefined) return '0s';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs > 0 ? `${hrs}h ` : ''}${mins > 0 ? `${mins}m ` : ''}${secs}s`;
  };

  const readinessScore = readiness?.score ?? 0;
  
  // Determine readiness score color
  const getReadinessColor = (score: number) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 70) return 'text-amber-400';
    return 'text-red-400';
  };

  const getReadinessBg = (score: number) => {
    if (score >= 90) return 'border-green-500/20 bg-green-950/20';
    if (score >= 70) return 'border-amber-500/20 bg-amber-950/20';
    return 'border-red-500/20 bg-red-950/20';
  };

  return (
    <div className="p-6 space-y-6 bg-[#11111b] min-h-screen">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-2 border-b border-[#313244]">
        <div>
          <h2 className="text-xl font-bold text-[#cdd6f4]">System Dashboard</h2>
          <p className="text-xs text-[#a6adc8] mt-1">Real-time status overview of local Taksh engine</p>
        </div>
        <div className="text-xs text-[#a6adc8] font-mono bg-[#181825] px-3 py-1.5 rounded-lg border border-[#313244]">
          Uptime: <span className="text-[#89b4fa] font-bold">{formatUptime(sysInfo?.uptime_seconds)}</span>
        </div>
      </div>

      {/* Overview Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Readiness Card */}
        <div className={`p-5 rounded-xl border ${getReadinessBg(readinessScore)} shadow-md flex items-center justify-between`}>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-[#a6adc8] uppercase tracking-wider">Readiness Score</h3>
            <div className="flex items-baseline gap-2">
              <span className={`text-4xl font-extrabold font-mono ${getReadinessColor(readinessScore)}`}>
                {readinessScore}%
              </span>
              <span className="text-xs text-[#a6adc8]">
                ({readiness?.status.toUpperCase()})
              </span>
            </div>
            <p className="text-[10px] text-[#a6adc8] mt-2">
              {readiness?.checks_passed} checks passed • {readiness?.checks_failed} failed • {readiness?.warnings} warnings
            </p>
          </div>
          <div className={`p-3 rounded-full bg-[#11111b]/50 ${getReadinessColor(readinessScore)}`}>
            <ShieldCheck className="w-10 h-10" />
          </div>
        </div>

        {/* System Stats Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-[#a6adc8] uppercase tracking-wider">System Health</h3>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${sysInfo?.health === 'healthy' ? 'text-green-400' : 'text-amber-400'}`}>
                {sysInfo?.health.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
            <div className="text-[10px] text-[#a6adc8] mt-2 flex flex-col gap-1">
              <span>FastAPI Backend Version: <strong className="text-[#cdd6f4]">{sysInfo?.version}</strong></span>
              <span>Uptime: <strong className="text-[#cdd6f4]">{formatUptime(sysInfo?.uptime_seconds)}</strong></span>
            </div>
          </div>
          <div className="p-3 rounded-full bg-[#11111b]/50 text-[#89b4fa]">
            <Server className="w-10 h-10" />
          </div>
        </div>

        {/* Runtime Statistics Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-[#a6adc8] uppercase tracking-wider">Runtime Activity</h3>
            <div className="grid grid-cols-2 gap-4 mt-2">
              <div>
                <span className="text-xs text-[#a6adc8] block">Active Sessions</span>
                <span className="text-lg font-bold font-mono text-[#cdd6f4]">
                  {sysInfo?.active_runtime_sessions ?? 0}
                </span>
              </div>
              <div>
                <span className="text-xs text-[#a6adc8] block">Memory Episodes</span>
                <span className="text-lg font-bold font-mono text-[#cba6f7]">
                  {sysInfo?.memory_episodes ?? 0}
                </span>
              </div>
            </div>
            <p className="text-[10px] text-[#a6adc8] mt-2">
              Active Provider Sessions: <strong className="text-[#cdd6f4]">{sysInfo?.active_provider_sessions ?? 0}</strong>
            </p>
          </div>
          <div className="p-3 rounded-full bg-[#11111b]/50 text-[#cba6f7]">
            <Cpu className="w-10 h-10" />
          </div>
        </div>
      </div>

      {/* Subsystems Health & Metadata Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Subsystems Health status */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md">
          <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
            <Database className="w-4 h-4 text-[#89b4fa]" />
            Subsystems Health Indicators
          </h3>
          <div className="space-y-3">
            {health && health.components ? (
              Object.entries(health.components).map(([name, status]) => (
                <div key={name} className="flex justify-between items-center p-2.5 rounded bg-[#11111b]/50 border border-[#313244]">
                  <span className="text-xs font-semibold capitalize text-[#cdd6f4]">{name}</span>
                  <div className="flex items-center gap-1.5">
                    {status === 'healthy' ? (
                      <>
                        <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                        <span className="text-xs text-green-400 font-medium">HEALTHY</span>
                      </>
                    ) : status === 'degraded' ? (
                      <>
                        <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                        <span className="text-xs text-amber-400 font-medium">DEGRADED</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3.5 h-3.5 text-red-400" />
                        <span className="text-xs text-red-400 font-medium">UNHEALTHY</span>
                      </>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#a6adc8]">No subsystem health data available.</p>
            )}
          </div>
        </div>

        {/* Release Metadata Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md">
          <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
            <Milestone className="w-4 h-4 text-[#cba6f7]" />
            Taksh Build Release Metadata
          </h3>
          {release ? (
            <div className="space-y-3 text-xs text-[#a6adc8]">
              <div className="grid grid-cols-2 gap-y-2 border-b border-[#313244] pb-3 mb-3">
                <span>Release Version:</span>
                <span className="text-[#cdd6f4] font-semibold font-mono">{release.version}</span>

                <span>Release Type:</span>
                <span className="text-[#cdd6f4] font-semibold font-mono capitalize">
                  {release.release_type || 'Production'}
                </span>

                <span>Alembic DB Revision:</span>
                <span className="text-[#cdd6f4] font-semibold font-mono">{release.schema_version}</span>

                <span>Build Timestamp:</span>
                <span className="text-[#cdd6f4] font-semibold font-mono">
                  {new Date(release.build_date).toLocaleString()}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase text-[#585b70] tracking-wider block mb-2">
                  Completed Build Milestones
                </span>
                <div className="flex flex-wrap gap-1.5 max-h-[120px] overflow-y-auto pr-1">
                  {(release.milestones_completed || release.completed_milestones || []).map((m) => (
                    <span
                      key={m}
                      className="px-2 py-0.5 rounded bg-[#313244] border border-[#45475a] text-[#cdd6f4] text-[10px] font-mono"
                    >
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-[#a6adc8]">No build metadata loaded.</p>
          )}
        </div>
      </div>
    </div>
  );
};
