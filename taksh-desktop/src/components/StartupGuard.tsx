import React from 'react';
import { ShieldAlert, ServerCrash, RefreshCw } from 'lucide-react';
import { ConnectionState } from '../services/backend';
import { ReadinessResponse } from '../types/backend';

interface StartupGuardProps {
  connectionState: ConnectionState;
  readiness: ReadinessResponse | null;
  isLoading: boolean;
  onRetry: () => void;
  children: React.ReactNode;
}

export const StartupGuard: React.FC<StartupGuardProps> = ({
  connectionState,
  readiness,
  isLoading,
  onRetry,
  children,
}) => {
  // If we are currently loading or connecting for the first time, show a loading spinner
  if (isLoading && connectionState === 'CONNECTING') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#1e1e2e] text-[#cdd6f4]">
        <RefreshCw className="w-12 h-12 text-[#cba6f7] animate-spin mb-4" />
        <h3 className="text-lg font-semibold">Connecting to Taksh backend...</h3>
        <p className="text-sm text-[#a6adc8] mt-1">Establishing secure local bridge</p>
      </div>
    );
  }

  // Blocked Mode: Backend Disconnected
  if (connectionState === 'DISCONNECTED' || connectionState === 'ERROR') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#1e1e2e] text-[#cdd6f4] p-6 text-center">
        <div className="p-4 bg-red-950/50 border border-red-500/30 rounded-full mb-6 text-red-400">
          <ServerCrash className="w-16 h-16" />
        </div>
        <h1 className="text-2xl font-bold text-red-400">Backend Offline</h1>
        <p className="max-w-md text-sm text-[#a6adc8] mt-3">
          Taksh Desktop requires the local backend server to be running.
          Please ensure that the FastAPI backend is started and reachable on your configured port.
        </p>
        <button
          onClick={onRetry}
          disabled={isLoading}
          className="flex items-center gap-2 mt-8 px-6 py-2.5 bg-[#89b4fa] hover:bg-[#b4befe] text-[#11111b] font-semibold rounded-lg shadow-md transition-all duration-200 disabled:opacity-50"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Reconnect Now
        </button>
      </div>
    );
  }

  // Blocked Mode: Readiness Score < 70
  if (readiness && readiness.score < 70) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#1e1e2e] text-[#cdd6f4] p-6 text-center">
        <div className="p-4 bg-purple-950/50 border border-purple-500/30 rounded-full mb-6 text-[#cba6f7]">
          <ShieldAlert className="w-16 h-16" />
        </div>
        <h1 className="text-2xl font-bold text-[#cba6f7]">System Not Ready</h1>
        <div className="mt-3 max-w-md">
          <p className="text-sm text-[#a6adc8]">
            The backend loaded, but one or more critical pre-flight checks failed.
          </p>
          <div className="mt-4 p-4 bg-[#11111b] rounded-lg border border-[#313244] text-left">
            <div className="flex justify-between items-center text-xs text-[#a6adc8] border-b border-[#313244] pb-2 mb-2 font-mono">
              <span>Readiness Score:</span>
              <span className="text-red-400 font-bold">{readiness.score}%</span>
            </div>
            <div className="flex justify-between text-xs text-[#a6adc8] mt-1.5">
              <span>Checks Passed:</span>
              <span className="text-green-400">{readiness.checks_passed}</span>
            </div>
            <div className="flex justify-between text-xs text-[#a6adc8] mt-1.5">
              <span>Checks Failed:</span>
              <span className="text-red-400">{readiness.checks_failed}</span>
            </div>
            <div className="flex justify-between text-xs text-[#a6adc8] mt-1.5">
              <span>Warnings:</span>
              <span className="text-amber-400">{readiness.warnings}</span>
            </div>
          </div>
        </div>
        <button
          onClick={onRetry}
          disabled={isLoading}
          className="flex items-center gap-2 mt-8 px-6 py-2.5 bg-[#cba6f7] hover:bg-[#f5c2e7] text-[#11111b] font-semibold rounded-lg shadow-md transition-all duration-200 disabled:opacity-50"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Recheck Health Status
        </button>
      </div>
    );
  }

  // Readiness >= 70 (either warning mode or healthy), allow UI
  return <>{children}</>;
};
