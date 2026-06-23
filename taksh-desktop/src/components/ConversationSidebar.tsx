import React, { useState, useMemo } from 'react';
import { Plus, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { ConversationSessionResponse } from '../types/backend';

interface ConversationSidebarProps {
  sessions: ConversationSessionResponse[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewConversation: () => void;
  currentPage: number;
  totalSessions: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewConversation,
  currentPage,
  totalSessions,
  pageSize,
  onPageChange
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter sessions client-side
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const query = searchQuery.toLowerCase();
    return sessions.filter((s) => {
      const titleMatch = (s.conversation_title || '').toLowerCase().includes(query);
      const lastMsgMatch = (s.last_message || '').toLowerCase().includes(query);
      const idMatch = s.runtime_session_id.toLowerCase().includes(query);
      return titleMatch || lastMsgMatch || idMatch;
    });
  }, [sessions, searchQuery]);

  // Grouping helper
  const groupedSessions = useMemo(() => {
    const today: ConversationSessionResponse[] = [];
    const yesterday: ConversationSessionResponse[] = [];
    const older: ConversationSessionResponse[] = [];

    const now = new Date();
    const todayStr = now.toDateString();
    
    const yesterdayDate = new Date();
    yesterdayDate.setDate(now.getDate() - 1);
    const yesterdayStr = yesterdayDate.toDateString();

    filteredSessions.forEach((s) => {
      try {
        const startedDate = new Date(s.started_at);
        const startedStr = startedDate.toDateString();

        if (startedStr === todayStr) {
          today.push(s);
        } else if (startedStr === yesterdayStr) {
          yesterday.push(s);
        } else {
          older.push(s);
        }
      } catch {
        older.push(s);
      }
    });

    return { today, yesterday, older };
  }, [filteredSessions]);

  const totalPages = Math.max(1, Math.ceil(totalSessions / pageSize));

  // Render list item helper
  const renderSessionItem = (s: ConversationSessionResponse) => {
    const isActive = s.runtime_session_id === activeSessionId;
    const displayName = s.conversation_title || `Chat: ${s.runtime_session_id.substring(0, 8)}...`;
    
    // Format timestamp
    let formattedTime = '';
    try {
      const d = new Date(s.started_at);
      formattedTime = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      formattedTime = '';
    }

    return (
      <button
        key={s.runtime_session_id}
        onClick={() => onSelectSession(s.runtime_session_id)}
        className={`w-full text-left p-3 rounded-xl transition-all duration-200 border flex flex-col gap-1.5 focus:outline-none ${
          isActive
            ? 'bg-[#313244] border-[#cba6f7] text-[#cdd6f4]'
            : 'bg-[#181825]/40 hover:bg-[#181825]/80 border-transparent text-[#a6adc8] hover:text-[#cdd6f4]'
        }`}
      >
        <div className="flex items-center justify-between w-full gap-2">
          <span className="font-semibold text-xs truncate max-w-[140px]" title={displayName}>
            {displayName}
          </span>
          <span className="text-[10px] opacity-75 font-mono select-none flex-shrink-0">{formattedTime}</span>
        </div>
        <div className="text-[11px] truncate opacity-80 w-full min-h-[16px] leading-tight font-sans">
          {s.last_message || <span className="italic opacity-60">No messages yet</span>}
        </div>
      </button>
    );
  };

  return (
    <div className="w-72 bg-[#1e1e2e] border-r border-[#313244] flex flex-col justify-between flex-shrink-0">
      {/* Top Section */}
      <div className="p-4 space-y-4 flex-1 flex flex-col overflow-hidden">
        {/* New Chat Button */}
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 py-3 bg-[#cba6f7] hover:bg-[#b4befe] text-[#11111b] rounded-xl text-sm font-bold shadow-md hover:shadow-lg transition-all duration-200 active:scale-[0.98]"
        >
          <Plus className="w-4 h-4 stroke-[3]" />
          New Conversation
        </button>

        {/* Client-side Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-[#585b70]" />
          <input
            type="text"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-[#11111b] border border-[#313244] focus:border-[#cba6f7] rounded-xl text-xs text-[#cdd6f4] placeholder-[#585b70] focus:outline-none transition-colors font-sans"
          />
        </div>

        {/* Sessions list grouped by dates */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 scrollbar-thin">
          {/* Today */}
          {groupedSessions.today.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="px-2 text-[10px] font-bold text-[#585b70] uppercase tracking-wider select-none">
                Today
              </h4>
              {groupedSessions.today.map(renderSessionItem)}
            </div>
          )}

          {/* Yesterday */}
          {groupedSessions.yesterday.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="px-2 text-[10px] font-bold text-[#585b70] uppercase tracking-wider select-none">
                Yesterday
              </h4>
              {groupedSessions.yesterday.map(renderSessionItem)}
            </div>
          )}

          {/* Older */}
          {groupedSessions.older.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="px-2 text-[10px] font-bold text-[#585b70] uppercase tracking-wider select-none">
                Older
              </h4>
              {groupedSessions.older.map(renderSessionItem)}
            </div>
          )}

          {filteredSessions.length === 0 && (
            <div className="p-8 text-center text-xs text-[#585b70] italic font-sans">
              No conversations found
            </div>
          )}
        </div>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-[#313244] bg-[#181825]/40 flex items-center justify-between text-xs text-[#a6adc8]">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="p-1.5 hover:bg-[#313244] rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Previous Page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <span className="font-mono text-[10px]">
          PAGE {currentPage} OF {totalPages}
        </span>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="p-1.5 hover:bg-[#313244] rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Next Page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
