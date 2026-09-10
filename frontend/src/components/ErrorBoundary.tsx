import { Component, type ReactNode } from 'react';

interface Props { children: ReactNode }
interface State { error: Error | null }

// Catches render crashes so the app shows a message instead of a blank page.
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error('Re:Route AI render error:', error);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'system-ui', color: '#e7ecf7', background: '#0b1020', minHeight: '100vh' }}>
          <h1 style={{ fontSize: 20 }}>Something went wrong rendering the app</h1>
          <p style={{ color: '#f87171' }}>{this.state.error.message}</p>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#97a3c4' }}>{this.state.error.stack}</pre>
          <button onClick={() => location.reload()} style={{ marginTop: 12, padding: '8px 14px' }}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}
