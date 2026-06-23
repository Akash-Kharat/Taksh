import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Send, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { conversationApi } from '../services/api/conversationApi';
import { SimulatedStreamProvider } from '../services/api/chatApi';
import { ConversationSidebar } from '../components/ConversationSidebar';
import { MessageBubble } from '../components/MessageBubble';
import { TypingIndicator, TypingStage } from '../components/TypingIndicator';
import { ConversationDiagnostics } from '../components/ConversationDiagnostics';
import { ConversationErrorBoundary } from '../components/ConversationErrorBoundary';
import { ConversationTurnSchema } from '../types/backend';

export const ConversationPage: React.FC = () => {
  const queryClient = useQueryClient();
  
  // State
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [typingStage, setTypingStage] = useState<TypingStage>('THINKING');
  const [streamingText, setStreamingText] = useState('');
  
  // Diagnostics panel state
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [selectedTurn, setSelectedTurn] = useState<ConversationTurnSchema | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeStreamRef = useRef<SimulatedStreamProvider | null>(null);
  
  const pageSize = 15;

  // 1. Query paginated sessions list
  const {
    data: sessionsData,
    refetch: refetchSessions
  } = useQuery({
    queryKey: ['conversationSessions', currentPage],
    queryFn: () => conversationApi.listSessions(currentPage, pageSize),
    refetchInterval: 15000 // Poll sessions list every 15 seconds
  });

  // 2. Query active session turns details
  const {
    data: sessionDetails,
    isLoading: isLoadingDetails,
    isError: isErrorDetails,
    refetch: refetchDetails
  } = useQuery({
    queryKey: ['sessionDetails', activeSessionId],
    queryFn: () => conversationApi.getSession(activeSessionId!),
    enabled: !!activeSessionId
  });

  // Scroll to bottom on messages load
  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [sessionDetails?.turns, streamingText, isTyping]);

  // Clean up active streams and stop session on unmount
  useEffect(() => {
    return () => {
      if (activeStreamRef.current) {
        activeStreamRef.current.cancel();
      }
      if (activeSessionId) {
        // Stop session when leaving conversation page
        conversationApi.stop(activeSessionId).catch((err) => {
          console.error('Failed to stop session on unmount:', err);
        });
      }
    };
  }, [activeSessionId]);

  // Create new session mutation
  const startSessionMutation = useMutation({
    mutationFn: () => conversationApi.start(),
    onSuccess: (data) => {
      // If we had a previous session active, stop it first
      if (activeSessionId) {
        conversationApi.stop(activeSessionId).catch((err) => {
          console.error('Error stopping previous session:', err);
        });
      }
      
      setActiveSessionId(data.runtime_session_id);
      queryClient.invalidateQueries({ queryKey: ['conversationSessions'] });
      setInputText('');
      setStreamingText('');
      setIsTyping(false);
      setSelectedTurn(null);
    }
  });

  // Handle Session Change
  const handleSelectSession = async (id: string) => {
    if (id === activeSessionId) return;

    if (activeSessionId) {
      // Gracefully stop old session (Revision 1)
      try {
        await conversationApi.stop(activeSessionId);
      } catch (err) {
        console.error('Error stopping old session:', err);
      }
    }

    if (activeStreamRef.current) {
      activeStreamRef.current.cancel();
      activeStreamRef.current = null;
    }

    setActiveSessionId(id);
    setStreamingText('');
    setIsTyping(false);
    setSelectedTurn(null);
  };

  // Send message turn execution
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isTyping || !activeSessionId) return;

    const message = inputText.trim();
    setInputText('');
    setIsTyping(true);
    setStreamingText('');
    setTypingStage('THINKING');

    // 1. Immediate local UI turn appending isn't needed as we poll or wait for complete,
    // but to simulate typing indicator stages:
    const stageTimers: any[] = [];
    
    // Simulate cognitive stages (Revision 3)
    stageTimers.push(setTimeout(() => setTypingStage('RETRIEVING_MEMORY'), 400));
    stageTimers.push(setTimeout(() => setTypingStage('SEARCHING_KNOWLEDGE'), 850));
    stageTimers.push(setTimeout(() => setTypingStage('GENERATING_RESPONSE'), 1300));

    // 2. Initialize simulated stream provider
    const stream = new SimulatedStreamProvider(message, activeSessionId);
    activeStreamRef.current = stream;

    stream.onChunk((chunk) => {
      setStreamingText((prev) => prev + chunk);
    });

    stream.onComplete(async (_fullText) => {
      stageTimers.forEach(clearTimeout);
      setIsTyping(false);
      setStreamingText('');
      activeStreamRef.current = null;

      // Invalidate queries to fetch latest Turn records including the completed turn
      await queryClient.invalidateQueries({ queryKey: ['sessionDetails', activeSessionId] });
      await queryClient.invalidateQueries({ queryKey: ['conversationSessions'] });
    });

    stream.onError((err) => {
      stageTimers.forEach(clearTimeout);
      setIsTyping(false);
      setStreamingText('');
      activeStreamRef.current = null;
      console.error('Streaming error caught:', err);
      alert('Error generating response: ' + (err.message || 'Check connection.'));
    });

    try {
      // 3. Inject message to conversation coordinator pipeline first (returns right away)
      await conversationApi.message(activeSessionId, message);
      
      // 4. Start stream generator simulation
      await stream.start();
    } catch (err: any) {
      stageTimers.forEach(clearTimeout);
      setIsTyping(false);
      activeStreamRef.current = null;
      console.error('Error sending message:', err);
      alert('Failed to send message turn: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleNewConversation = () => {
    startSessionMutation.mutate();
  };

  const handleSelectDiagnostics = (turn: ConversationTurnSchema) => {
    setSelectedTurn(turn);
    setShowDiagnostics(true);
  };

  // Compile active session info for diagnostics
  const activeSessionInfo = sessionDetails
    ? {
        sessionId: activeSessionId || '',
        turnsCount: sessionDetails.turns.length,
        metrics: sessionDetails.metrics,
        totalInterruptions: sessionDetails.interruptions
      }
    : null;

  return (
    <ConversationErrorBoundary
      onRetry={() => {
        refetchSessions();
        if (activeSessionId) refetchDetails();
      }}
      onNewSession={handleNewConversation}
    >
      <div className="flex flex-1 h-[calc(100vh-2rem)] overflow-hidden bg-[#11111b]">
        {/* Session Sidebar */}
        <ConversationSidebar
          sessions={sessionsData?.items || []}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewConversation={handleNewConversation}
          currentPage={currentPage}
          totalSessions={sessionsData?.total || 0}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
        />

        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#11111b] relative">
          {activeSessionId ? (
            <>
              {/* Messages viewport */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 pr-3 scrollbar-thin">
                {isLoadingDetails ? (
                  <div className="flex flex-col items-center justify-center h-full text-xs text-[#a6adc8] font-mono gap-3">
                    <RefreshCw className="w-5 h-5 animate-spin text-[#cba6f7]" />
                    <span>Loading conversation history...</span>
                  </div>
                ) : isErrorDetails ? (
                  <div className="flex flex-col items-center justify-center h-full text-xs text-red-400 font-mono gap-3">
                    <AlertCircle className="w-6 h-6 text-red-400 animate-pulse" />
                    <span>Failed to retrieve conversation history.</span>
                  </div>
                ) : (
                  <>
                    {sessionDetails?.turns.length === 0 && !isTyping && (
                      <div className="flex flex-col items-center justify-center h-full text-center max-w-sm mx-auto space-y-4">
                        <div className="p-3.5 bg-[#1e1e2e] border border-[#313244] rounded-2xl text-[#cba6f7] shadow-md">
                          <Sparkles className="w-6 h-6 animate-pulse" />
                        </div>
                        <h3 className="font-bold text-sm text-[#f5c2e7]">New Conversation Started</h3>
                        <p className="text-xs text-[#a6adc8] leading-relaxed">
                          Taksh is listening. Send your first query below to begin engineering, diagnostic, or memory recalls.
                        </p>
                      </div>
                    )}
                    
                    {/* Render Turns */}
                    {sessionDetails?.turns.map((turn) => (
                      <React.Fragment key={turn.turn_id}>
                        <MessageBubble
                          role="user"
                          content={turn.user_text}
                          timestamp={turn.started_at}
                        />
                        <MessageBubble
                          role="assistant"
                          content={turn.assistant_text}
                          timestamp={turn.completed_at}
                          promptTokens={turn.prompt_tokens}
                          completionTokens={turn.completion_tokens}
                          memoryHits={turn.memory_hits}
                          knowledgeHits={turn.knowledge_hits}
                          latencyMs={turn.latency_ms}
                          messageVersion={turn.message_version}
                          onSelectDiagnostics={() => handleSelectDiagnostics(turn)}
                        />
                      </React.Fragment>
                    ))}

                    {/* Simulated stream indicator */}
                    {isTyping && (
                      <>
                        <MessageBubble
                          role="user"
                          content={inputText /* fallback reference if input is already cleared */}
                          timestamp={new Date().toISOString()}
                        />
                        {typingStage === 'GENERATING_RESPONSE' && streamingText ? (
                          <MessageBubble
                            role="assistant"
                            content={streamingText}
                            timestamp={new Date().toISOString()}
                          />
                        ) : (
                          <TypingIndicator stage={typingStage} />
                        )}
                      </>
                    )}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Chat Input Box */}
              <div className="p-4 border-t border-[#313244] bg-[#11111b] z-10">
                <form onSubmit={handleSendMessage} className="flex gap-3 max-w-4xl mx-auto">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type your message to Taksh..."
                    disabled={isTyping}
                    className="flex-1 px-4 py-3 bg-[#1e1e2e] border border-[#313244] focus:border-[#cba6f7] rounded-xl text-sm text-[#cdd6f4] placeholder-[#585b70] focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    type="submit"
                    disabled={!inputText.trim() || isTyping}
                    className="p-3 bg-[#cba6f7] hover:bg-[#b4befe] text-[#11111b] disabled:opacity-30 disabled:cursor-not-allowed rounded-xl transition-all duration-200 shadow-md hover:shadow-lg focus:outline-none flex items-center justify-center"
                  >
                    <Send className="w-4 h-4 stroke-[2.5]" />
                  </button>
                </form>
              </div>
            </>
          ) : (
            /* Splash page if no conversation selected */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto space-y-4 select-none">
              <div className="p-4 bg-[#1e1e2e] border border-[#313244] rounded-2xl text-[#cba6f7] shadow-md">
                <Sparkles className="w-8 h-8 animate-pulse" />
              </div>
              <h3 className="font-bold text-base text-[#f5c2e7] tracking-wide">Continuous Conversation Shell</h3>
              <p className="text-xs text-[#a6adc8] leading-relaxed">
                Restore previous chats or select "New Conversation" to create an active runtime state machine and continuous memory session.
              </p>
              <button
                onClick={handleNewConversation}
                className="mt-2 px-5 py-2.5 bg-[#cba6f7] hover:bg-[#b4befe] text-[#11111b] rounded-xl text-xs font-bold transition-all duration-200 active:scale-[0.98] shadow"
              >
                Create Conversation Session
              </button>
            </div>
          )}
        </div>

        {/* Collapsible Diagnostics Panel */}
        <ConversationDiagnostics
          isOpen={showDiagnostics}
          onClose={() => setShowDiagnostics(false)}
          sessionInfo={activeSessionInfo}
          selectedTurn={selectedTurn}
        />
      </div>
    </ConversationErrorBoundary>
  );
};
