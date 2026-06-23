import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Save, RefreshCw, Settings as SettingsIcon, Link, Info } from 'lucide-react';
import { systemApi } from '../services/api/systemApi';
import { getBackendUrl, saveBackendUrl } from '../services/backend';

export const Settings: React.FC = () => {
  // 1. Fetch system configs
  const { data: config, isLoading } = useQuery({
    queryKey: ['systemConfig'],
    queryFn: systemApi.getSystemConfig,
  });

  const [inputUrl, setInputUrl] = useState(getBackendUrl());
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    saveBackendUrl(inputUrl);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
    // Reload window after saving url to re-fetch queries with new client instance config
    setTimeout(() => window.location.reload(), 800);
  };

  const handleResetUrl = () => {
    saveBackendUrl(''); // Reset to default
    setInputUrl(getBackendUrl());
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
    setTimeout(() => window.location.reload(), 800);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-[#cba6f7] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-[#11111b] min-h-screen">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-2 border-b border-[#313244]">
        <div>
          <h2 className="text-xl font-bold text-[#cdd6f4]">System Settings</h2>
          <p className="text-xs text-[#a6adc8] mt-1">Configure backend connections and view active core settings</p>
        </div>
      </div>

      {/* Grid: URL Configuration & Read Only Settings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend URL configuration card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
              <Link className="w-4 h-4 text-[#89b4fa]" />
              Backend Connection Setup
            </h3>
            <p className="text-xs text-[#a6adc8] mb-4">
              Configure the connection URL for the Taksh local or remote backend engine. Changes are applied immediately on save.
            </p>

            <form onSubmit={handleSaveUrl} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs text-[#a6adc8] font-semibold block">Backend Server API URL</label>
                <input
                  type="text"
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  placeholder="e.g., http://127.0.0.1:8000"
                  className="w-full px-3 py-2 bg-[#11111b] border border-[#45475a] focus:border-[#cba6f7] rounded-lg text-xs font-mono text-[#cdd6f4] outline-none"
                  required
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  className="flex items-center gap-2 px-4 py-2 bg-[#cba6f7] hover:bg-[#f5c2e7] text-[#11111b] text-xs font-semibold rounded-lg shadow transition-all duration-200"
                >
                  <Save className="w-3.5 h-3.5" />
                  Save Connection Settings
                </button>
                <button
                  type="button"
                  onClick={handleResetUrl}
                  className="flex items-center gap-2 px-4 py-2 bg-[#313244] hover:bg-[#45475a] text-[#cdd6f4] text-xs font-semibold rounded-lg shadow transition-all duration-200"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Reset to Default
                </button>
              </div>
            </form>

            {saveSuccess && (
              <div className="mt-4 p-3 bg-green-950/40 border border-green-700/30 text-green-400 text-xs rounded-lg animate-pulse">
                Backend connection settings updated! Reloading interface...
              </div>
            )}
          </div>

          <div className="mt-6 p-3 bg-[#11111b]/50 border border-[#313244] rounded-lg flex gap-2.5 items-start">
            <Info className="w-4 h-4 text-[#89b4fa] flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-[#a6adc8]">
              Tauri prioritizes connection configs in this order: (1) local override, (2) env variables, (3) fallback (http://127.0.0.1:8000).
            </p>
          </div>
        </div>

        {/* Read-Only Configuration Card */}
        <div className="p-5 rounded-xl border border-[#313244] bg-[#1e1e2e] shadow-md">
          <h3 className="text-sm font-bold text-[#cdd6f4] border-b border-[#313244] pb-3 mb-4 flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-[#cba6f7]" />
            Active Core Config Snapshot
          </h3>
          <div className="space-y-2.5 text-xs text-[#a6adc8] max-h-[300px] overflow-y-auto pr-1">
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Environment Profile:</span>
              <span className="text-[#cdd6f4] font-semibold uppercase">{config?.environment}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Core Port:</span>
              <span className="text-[#cdd6f4] font-mono">{config?.port}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Host Interface:</span>
              <span className="text-[#cdd6f4] font-mono">{config?.host}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Log Level:</span>
              <span className="text-[#cdd6f4] font-semibold">{config?.log_level}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Provider Health Checks:</span>
              <span className="text-[#cdd6f4]">{config?.enable_provider_health_checks ? 'ENABLED' : 'DISABLED'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Max Prompt Length:</span>
              <span className="text-[#cdd6f4] font-mono">{config?.max_prompt_chars} chars</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#313244]/40">
              <span>Max Memory Items:</span>
              <span className="text-[#cdd6f4] font-mono">{config?.max_memory_items} items</span>
            </div>
            <div className="flex justify-between py-1">
              <span>Health Check Timeout:</span>
              <span className="text-[#cdd6f4] font-mono">{config?.health_check_timeout_seconds} seconds</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
