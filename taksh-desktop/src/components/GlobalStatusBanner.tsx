import React from 'react';
import { AlertCircle, WifiOff, Activity } from 'lucide-react';

export type GlobalHealthStatus = 'Healthy' | 'Degraded' | 'Disconnected' | 'Not Ready';

interface GlobalStatusBannerProps {
  status: GlobalHealthStatus;
  score?: number;
}

export const GlobalStatusBanner: React.FC<GlobalStatusBannerProps> = ({ status, score }) => {
  if (status === 'Healthy') {
    return null; // Don't show banner if completely healthy
  }

  let bannerClass = '';
  let icon = <AlertCircle className="w-5 h-5" />;
  let title = '';
  let description = '';

  switch (status) {
    case 'Disconnected':
      bannerClass = 'bg-red-950/80 border-red-700 text-red-200';
      icon = <WifiOff className="w-5 h-5 text-red-400" />;
      title = 'Backend Disconnected';
      description = 'Could not connect to the local Taksh backend. Make sure the backend server is running.';
      break;
    case 'Not Ready':
      bannerClass = 'bg-purple-950/80 border-purple-700 text-purple-200';
      icon = <Activity className="w-5 h-5 text-purple-400" />;
      title = `System Not Ready (Score: ${score ?? 0}%)`;
      description = 'One or more critical startup checks failed. Go to the Diagnostics page to investigate.';
      break;
    case 'Degraded':
      bannerClass = 'bg-amber-950/80 border-amber-700 text-amber-200';
      icon = <AlertCircle className="w-5 h-5 text-amber-400" />;
      title = `System Degraded (Score: ${score ?? 0}%)`;
      description = 'Some non-critical checks failed. The app remains functional but may experience limitations.';
      break;
  }

  return (
    <div className={`flex items-center gap-3 p-4 mx-6 mt-6 border rounded-lg backdrop-blur-md shadow-lg ${bannerClass} transition-all duration-300 animate-pulse`}>
      <div className="flex-shrink-0">{icon}</div>
      <div className="flex-grow">
        <h4 className="font-semibold text-sm">{title}</h4>
        <p className="text-xs opacity-90 mt-0.5">{description}</p>
      </div>
    </div>
  );
};
