import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  HeartPulse,
  Radio,
  Settings as SettingsIcon,
  MessageSquare,
  Mic,
  Brain,
  FolderCode,
  Wrench,
  Terminal
} from 'lucide-react';
import { GlobalStatusBanner, GlobalHealthStatus } from '../components/GlobalStatusBanner';

interface ShellLayoutProps {
  status: GlobalHealthStatus;
  score?: number;
  backendUrl: string;
  children: React.ReactNode;
}

export const ShellLayout: React.FC<ShellLayoutProps> = ({
  status,
  score,
  backendUrl,
  children,
}) => {
  const activeClass = 'flex items-center gap-3 px-4 py-2.5 bg-[#313244] text-[#cba6f7] rounded-lg text-sm font-medium transition-all duration-200';
  const inactiveClass = 'flex items-center gap-3 px-4 py-2.5 text-[#a6adc8] hover:bg-[#181825] hover:text-[#cdd6f4] rounded-lg text-sm font-medium transition-all duration-200';
  const disabledClass = 'flex items-center gap-3 px-4 py-2.5 text-[#585b70] cursor-not-allowed rounded-lg text-sm font-medium opacity-60';

  const statusColors = {
    Healthy: 'bg-green-500',
    Degraded: 'bg-amber-500',
    'Not Ready': 'bg-purple-500',
    Disconnected: 'bg-red-500',
  };

  return (
    <div className="flex min-h-screen bg-[#11111b] text-[#cdd6f4]">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-[#1e1e2e] border-r border-[#313244] flex flex-col justify-between flex-shrink-0">
        <div>
          {/* Logo / Header */}
          <div className="flex items-center gap-3 px-6 py-5 border-b border-[#313244]">
            <div className="p-2 bg-[#313244] rounded-lg text-[#cba6f7] shadow-inner">
              <Terminal className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-wide text-[#f5c2e7]">Taksh</h1>
              <span className="text-[10px] text-[#a6adc8] uppercase tracking-widest font-semibold">Desktop Client</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-6">
            {/* System Group */}
            <div>
              <span className="px-4 text-[10px] font-bold text-[#585b70] uppercase tracking-wider block mb-2">
                System
              </span>
              <div className="space-y-1">
                <NavLink
                  to="/"
                  className={({ isActive }) => (isActive ? activeClass : inactiveClass)}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </NavLink>
                <NavLink
                  to="/diagnostics"
                  className={({ isActive }) => (isActive ? activeClass : inactiveClass)}
                >
                  <HeartPulse className="w-4 h-4" />
                  Diagnostics
                </NavLink>
                <NavLink
                  to="/providers"
                  className={({ isActive }) => (isActive ? activeClass : inactiveClass)}
                >
                  <Radio className="w-4 h-4" />
                  Providers
                </NavLink>
                <NavLink
                  to="/settings"
                  className={({ isActive }) => (isActive ? activeClass : inactiveClass)}
                >
                  <SettingsIcon className="w-4 h-4" />
                  Settings
                </NavLink>
              </div>
            </div>

            {/* Future Modules Group */}
            <div>
              <div className="flex items-center justify-between px-4 mb-2">
                <span className="text-[10px] font-bold text-[#585b70] uppercase tracking-wider">
                  Future Modules
                </span>
                <span className="text-[8px] bg-[#313244] text-[#89b4fa] px-1.5 py-0.5 rounded font-mono">
                  v1.1+
                </span>
              </div>
              <div className="space-y-1">
                <div className={disabledClass} title="Available in future release">
                  <MessageSquare className="w-4 h-4" />
                  Conversation
                </div>
                <div className={disabledClass} title="Available in future release">
                  <Mic className="w-4 h-4" />
                  Voice Controls
                </div>
                <div className={disabledClass} title="Available in future release">
                  <Brain className="w-4 h-4" />
                  Memory Browser
                </div>
                <div className={disabledClass} title="Available in future release">
                  <FolderCode className="w-4 h-4" />
                  Workspace
                </div>
                <div className={disabledClass} title="Available in future release">
                  <Wrench className="w-4 h-4" />
                  Tools
                </div>
              </div>
            </div>
          </nav>
        </div>

        {/* Footer info & Connection Status */}
        <div className="p-4 border-t border-[#313244] bg-[#181825]/40 text-xs">
          <div className="flex items-center gap-2 mb-2 justify-between">
            <span className="text-[#a6adc8]">Connection State:</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${statusColors[status]}`} />
              <span className="font-semibold font-mono text-[10px] text-[#cdd6f4]">
                {status.toUpperCase()}
              </span>
            </div>
          </div>
          <div className="text-[10px] text-[#a6adc8] truncate font-mono" title={backendUrl}>
            API: {backendUrl}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-screen overflow-y-auto bg-[#11111b]">
        {/* Global health alert bar if status has issues */}
        <GlobalStatusBanner status={status} score={score} />

        {/* Page Content Container */}
        <div className="flex-1">
          {children}
        </div>
      </main>
    </div>
  );
};
