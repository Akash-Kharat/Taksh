import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  language: string;
  value: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language, value }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className="my-4 rounded-lg border border-[#313244] bg-[#11111b] overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#181825] text-xs text-[#a6adc8] font-mono border-b border-[#313244]">
        <span className="font-semibold select-none">{language || 'text'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 hover:text-[#cdd6f4] transition-colors focus:outline-none font-medium"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[#a6e3a1]" />
              <span className="text-[#a6e3a1]">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      
      {/* Code contents with horizontal scroll */}
      <div className="p-4 overflow-x-auto font-mono text-sm text-[#cdd6f4] leading-relaxed">
        <pre className="m-0 whitespace-pre">
          <code>{value}</code>
        </pre>
      </div>
    </div>
  );
};
