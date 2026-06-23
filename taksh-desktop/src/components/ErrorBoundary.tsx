import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 m-6 bg-[#181825] border border-red-500/20 rounded-xl text-[#cdd6f4] text-center shadow-lg">
          <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-full mb-4 text-red-400">
            <AlertTriangle className="w-10 h-10" />
          </div>
          <h2 className="text-lg font-bold text-red-400">Interface Render Failed</h2>
          <p className="max-w-md text-xs text-[#a6adc8] mt-2">
            An unexpected error occurred while drawing this component. This is usually due to a missing property or mismatch in the backend response format.
          </p>
          {this.state.error && (
            <pre className="mt-4 p-3 bg-[#11111b] rounded border border-[#313244] text-[10px] text-left text-red-300 font-mono max-w-full overflow-auto max-h-[150px]">
              {this.state.error.toString()}
            </pre>
          )}
          <button
            onClick={this.handleReload}
            className="flex items-center gap-2 mt-6 px-4 py-2 bg-[#f38ba8] hover:bg-[#eba0b2] text-[#11111b] text-xs font-semibold rounded-lg shadow-sm transition-all duration-200"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reload Interface
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
