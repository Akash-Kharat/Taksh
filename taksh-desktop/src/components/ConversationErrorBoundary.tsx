import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw, MessageSquarePlus } from 'lucide-react';

interface Props {
  children?: ReactNode;
  onRetry?: () => void;
  onNewSession?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ConversationErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Conversation component caught exception:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[#11111b] text-[#cdd6f4] min-h-[500px]">
          <div className="max-w-md w-full bg-[#1e1e2e] border border-[#313244] rounded-2xl p-6 shadow-xl space-y-6 text-center">
            {/* Warning Icon */}
            <div className="mx-auto w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <AlertCircle className="w-6 h-6 animate-bounce" />
            </div>

            {/* Error Message */}
            <div className="space-y-2">
              <h3 className="font-bold text-lg text-[#f5c2e7]">Conversation Pipeline Error</h3>
              <p className="text-xs text-[#a6adc8] leading-relaxed">
                The connection to the backend orchestrator was interrupted, or a provider session failed to initialize.
              </p>
              {this.state.error && (
                <div className="text-[10px] bg-[#11111b] text-red-300 font-mono p-3 rounded-lg border border-[#313244] text-left overflow-x-auto max-h-24">
                  {this.state.error.message || String(this.state.error)}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2 justify-center">
              <button
                onClick={this.handleReset}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-[#313244] hover:bg-[#45475a] text-[#cdd6f4] rounded-lg text-sm font-semibold transition-all duration-200"
              >
                <RefreshCw className="w-4 h-4" />
                Retry Connection
              </button>
              
              {this.props.onNewSession && (
                <button
                  onClick={() => {
                    this.setState({ hasError: false, error: null });
                    if (this.props.onNewSession) this.props.onNewSession();
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-[#cba6f7] hover:bg-[#b4befe] text-[#11111b] rounded-lg text-sm font-semibold transition-all duration-200"
                >
                  <MessageSquarePlus className="w-4 h-4" />
                  New Session
                </button>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
