import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from './CodeBlock';
import { User, Cpu } from 'lucide-react';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  promptTokens?: number | null;
  completionTokens?: number | null;
  memoryHits?: number | null;
  knowledgeHits?: number | null;
  latencyMs?: number;
  messageVersion?: number;
  onSelectDiagnostics?: () => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  content,
  timestamp,
  promptTokens: _promptTokens,
  completionTokens: _completionTokens,
  memoryHits: _memoryHits,
  knowledgeHits: _knowledgeHits,
  latencyMs,
  messageVersion,
  onSelectDiagnostics
}) => {
  const isUser = role === 'user';

  // Format time helper
  const formatTime = (timeStr?: string) => {
    if (!timeStr) return '';
    try {
      const date = new Date(timeStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className={`flex w-full gap-3 my-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Icon Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[#313244] border border-[#45475a] flex items-center justify-center text-[#cba6f7] shadow-sm">
          <Cpu className="w-4 h-4" />
        </div>
      )}

      {/* Message Box */}
      <div className={`max-w-[75%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`px-4 py-3 rounded-2xl shadow-sm text-sm leading-relaxed break-words ${
            isUser
              ? 'bg-[#cba6f7] text-[#11111b] rounded-tr-none font-medium'
              : 'bg-[#1e1e2e] text-[#cdd6f4] border border-[#313244] rounded-tl-none'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose prose-invert max-w-none text-xs md:text-sm prose-p:my-1 prose-pre:bg-transparent prose-pre:p-0">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                skipHtml={true}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    const language = match ? match[1] : '';
                    const value = String(children).replace(/\n$/, '');
                    const isInline = !className;
                    return !isInline ? (
                      <CodeBlock language={language} value={value} />
                    ) : (
                      <code className="bg-[#313244] px-1.5 py-0.5 rounded text-[#f5c2e7] font-mono text-xs" {...props}>
                        {children}
                      </code>
                    );
                  },
                  p({ children }) {
                    return <p className="mb-2 last:mb-0">{children}</p>;
                  },
                  ul({ children }) {
                    return <ul className="list-disc pl-5 mb-2">{children}</ul>;
                  },
                  ol({ children }) {
                    return <ol className="list-decimal pl-5 mb-2">{children}</ol>;
                  },
                  li({ children }) {
                    return <li className="mb-1">{children}</li>;
                  },
                  h1({ children }) { return <h1 className="text-lg font-bold mt-3 mb-1 text-[#f5c2e7] border-b border-[#313244] pb-1">{children}</h1>; },
                  h2({ children }) { return <h2 className="text-base font-bold mt-2 mb-1 text-[#cba6f7]">{children}</h2>; },
                  h3({ children }) { return <h3 className="text-sm font-semibold mt-2 mb-1 text-[#89b4fa]">{children}</h3>; },
                  table({ children }) {
                    return (
                      <div className="overflow-x-auto my-3 border border-[#313244] rounded-lg">
                        <table className="w-full text-left border-collapse text-xs">{children}</table>
                      </div>
                    );
                  },
                  thead({ children }) { return <thead className="bg-[#181825] border-b border-[#313244]">{children}</thead>; },
                  tbody({ children }) { return <tbody className="divide-y divide-[#313244]">{children}</tbody>; },
                  th({ children }) { return <th className="px-3 py-2 font-bold text-[#f5c2e7]">{children}</th>; },
                  td({ children }) { return <td className="px-3 py-2 text-[#a6adc8]">{children}</td>; }
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Telemetry metadata footer for Assistant messages */}
        <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[#a6adc8] select-none font-mono">
          <span>{formatTime(timestamp)}</span>
          {messageVersion && messageVersion > 1 && (
            <span className="bg-[#313244] text-[#89b4fa] px-1 rounded">v{messageVersion}</span>
          )}
          {!isUser && onSelectDiagnostics && (
            <button
              onClick={onSelectDiagnostics}
              className="text-[#cba6f7] hover:underline cursor-pointer hover:text-[#f5c2e7] transition-colors flex items-center gap-0.5"
              title="Click to view full turn diagnostics"
            >
              • Turn Diagnostics
            </button>
          )}
          {!isUser && latencyMs !== undefined && (
            <span className="text-[#585b70]">({Math.round(latencyMs)}ms)</span>
          )}
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[#cba6f7] flex items-center justify-center text-[#11111b] shadow-sm">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
