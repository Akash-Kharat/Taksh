import React from 'react';
import { X, Cpu } from 'lucide-react';
import { ConversationTurnSchema, ConversationMetricsSchema } from '../types/backend';

interface ConversationDiagnosticsProps {
  isOpen: boolean;
  onClose: () => void;
  sessionInfo: {
    sessionId: string;
    turnsCount: number;
    activeProvider?: string;
    metrics?: ConversationMetricsSchema | null;
    totalInterruptions?: number;
  } | null;
  selectedTurn: ConversationTurnSchema | null;
}

export const ConversationDiagnostics: React.FC<ConversationDiagnosticsProps> = ({
  isOpen,
  onClose,
  sessionInfo,
  selectedTurn
}) => {
  if (!isOpen) return null;

  return (
    <aside className="w-80 bg-[#1e1e2e] border-l border-[#313244] flex flex-col flex-shrink-0 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#313244]">
        <h3 className="font-bold text-sm text-[#f5c2e7] tracking-wider uppercase flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          Diagnostics
        </h3>
        <button
          onClick={onClose}
          className="text-[#a6adc8] hover:text-[#cdd6f4] transition-colors p-1 hover:bg-[#313244] rounded-lg"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs text-[#cdd6f4]">
        {/* Selected Turn Section */}
        {selectedTurn ? (
          <div className="space-y-4">
            <h4 className="font-bold text-[10px] text-[#585b70] uppercase tracking-wider">
              Selected Turn Details
            </h4>
            <div className="bg-[#181825] border border-[#313244] rounded-lg p-3.5 space-y-3">
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Turn ID:</span>
                <span className="font-mono text-[#cba6f7] truncate max-w-[150px]" title={selectedTurn.turn_id}>
                  {selectedTurn.turn_id}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Provider / Model:</span>
                <span className="text-right font-medium text-[#89b4fa]">
                  {selectedTurn.provider_name || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Latency:</span>
                <span className="font-mono text-[#a6e3a1] font-semibold">
                  {selectedTurn.latency_ms ? `${Math.round(selectedTurn.latency_ms)}ms` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Prompt Tokens:</span>
                <span className="font-mono font-medium text-[#f9e2af]">
                  {selectedTurn.prompt_tokens ?? '0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Completion Tokens:</span>
                <span className="font-mono font-medium text-[#f9e2af]">
                  {selectedTurn.completion_tokens ?? '0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Episodic Memory Hits:</span>
                <span className="font-mono font-medium text-[#f5c2e7]">
                  {selectedTurn.memory_hits ?? '0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Knowledge Chunk Hits:</span>
                <span className="font-mono font-medium text-[#89b4fa]">
                  {selectedTurn.knowledge_hits ?? '0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Segments Synthesized:</span>
                <span className="font-mono">{selectedTurn.segment_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Budget Truncated:</span>
                <span className={`font-semibold ${selectedTurn.response_truncated ? 'text-red-400' : 'text-[#a6e3a1]'}`}>
                  {selectedTurn.response_truncated ? 'YES' : 'NO'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-3 bg-[#181825]/40 text-[#a6adc8] italic rounded-lg text-center select-none font-mono">
            Click "Turn Diagnostics" on any assistant message to view performance telemetry.
          </div>
        )}

        {/* Global Session Section */}
        {sessionInfo && (
          <div className="space-y-4 pt-4 border-t border-[#313244]">
            <h4 className="font-bold text-[10px] text-[#585b70] uppercase tracking-wider">
              Active Session Telemetry
            </h4>
            <div className="bg-[#181825] border border-[#313244] rounded-lg p-3.5 space-y-3">
              <div className="flex flex-col gap-1">
                <span className="text-[#a6adc8]">Session ID:</span>
                <span className="font-mono text-[#cdd6f4] select-all break-all text-[10px] bg-[#11111b] p-1.5 rounded border border-[#313244]">
                  {sessionInfo.sessionId}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Total Turns:</span>
                <span className="font-semibold text-[#f5c2e7]">{sessionInfo.turnsCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Avg Turn Latency:</span>
                <span className="font-mono text-[#a6e3a1]">
                  {sessionInfo.metrics?.average_turn_latency_ms
                    ? `${Math.round(sessionInfo.metrics.average_turn_latency_ms)}ms`
                    : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a6adc8]">Interruptions Count:</span>
                <span className="font-semibold text-red-400">
                  {sessionInfo.metrics?.total_interruptions ?? sessionInfo.totalInterruptions ?? 0}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
