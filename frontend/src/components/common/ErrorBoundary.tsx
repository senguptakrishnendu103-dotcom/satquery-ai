import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error caught by ErrorBoundary:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    } else {
      window.location.reload();
    }
  };

  public override render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[300px] w-full flex-col items-center justify-center rounded-2xl border border-rose-500/30 bg-sat-surface/95 p-8 text-center shadow-2xl backdrop-blur-md">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-400 mb-4">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h2 className="text-base font-bold text-sat-text tracking-wide mb-1">
            {this.props.fallbackTitle || 'Component Render Interrupted'}
          </h2>
          <p className="max-w-md text-xs text-sat-muted mb-4">
            {this.state.error?.message || 'An unexpected rendering error occurred in this workspace view.'}
          </p>
          <button
            type="button"
            onClick={this.handleReset}
            className="flex items-center gap-2 rounded-xl bg-sat-accent px-4 py-2 text-xs font-bold text-slate-950 transition-all hover:bg-sat-accent/90"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reload Workspace
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
