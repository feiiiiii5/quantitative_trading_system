import { Component, type ReactNode, type ErrorInfo } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  resetKey?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  resetErrorBoundary = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          minHeight: '100vh', background: '#0a0a0f', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif',
          padding: '2rem', gap: '1rem',
        }}>
          <h2 style={{ color: '#FF1744', fontSize: '1.5rem', margin: 0 }}>Something went wrong</h2>
          <p style={{ color: 'rgba(255,255,255,0.6)', maxWidth: '400px', textAlign: 'center', margin: 0 }}>
            {this.state.error?.message ?? 'An unexpected error occurred'}
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button onClick={this.resetErrorBoundary} style={{
              padding: '0.5rem 1.5rem', background: '#2962FF', color: '#fff', border: 'none',
              borderRadius: '6px', cursor: 'pointer', fontSize: '0.875rem',
            }}>
              Retry
            </button>
            <a href="/" style={{
              padding: '0.5rem 1.5rem', background: 'rgba(255,255,255,0.1)', color: '#e0e0e0',
              borderRadius: '6px', textDecoration: 'none', fontSize: '0.875rem',
            }}>
              Go Home
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
