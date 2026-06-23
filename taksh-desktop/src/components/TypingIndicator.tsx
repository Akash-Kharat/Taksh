import React from 'react';
import { Cpu, Brain, Search, Sparkles } from 'lucide-react';

export type TypingStage = 'THINKING' | 'RETRIEVING_MEMORY' | 'SEARCHING_KNOWLEDGE' | 'GENERATING_RESPONSE';

interface TypingIndicatorProps {
  stage: TypingStage;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ stage }) => {
  const stageConfigs = {
    THINKING: {
      label: 'Taksh is thinking...',
      icon: <Cpu className="w-4 h-4 text-[#cba6f7] animate-pulse" />,
      color: 'text-[#cba6f7]',
    },
    RETRIEVING_MEMORY: {
      label: 'Retrieving episodic memory...',
      icon: <Brain className="w-4 h-4 text-[#f5c2e7] animate-bounce" />,
      color: 'text-[#f5c2e7]',
    },
    SEARCHING_KNOWLEDGE: {
      label: 'Searching knowledge base...',
      icon: <Search className="w-4 h-4 text-[#89b4fa] animate-spin" />,
      color: 'text-[#89b4fa]',
    },
    GENERATING_RESPONSE: {
      label: 'Generating response...',
      icon: <Sparkles className="w-4 h-4 text-[#a6e3a1] animate-pulse" />,
      color: 'text-[#a6e3a1]',
    },
  };

  const config = stageConfigs[stage] || stageConfigs.THINKING;

  return (
    <div className="flex items-center gap-3 my-4 pl-1">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[#1e1e2e] border border-[#313244] flex items-center justify-center shadow-inner">
        {config.icon}
      </div>
      <div className="flex items-center gap-2 text-xs font-mono text-[#a6adc8]">
        <span className={config.color}>{config.label}</span>
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-[#585b70] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-1.5 h-1.5 bg-[#585b70] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-1.5 h-1.5 bg-[#585b70] rounded-full animate-bounce"></span>
        </div>
      </div>
    </div>
  );
};
