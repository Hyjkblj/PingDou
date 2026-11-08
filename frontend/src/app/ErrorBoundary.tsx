import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/Button';

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error(error, info); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="fatal-error">
        <AlertTriangle size={32} />
        <h1>页面遇到问题</h1>
        <p>{this.state.error.message}</p>
        <Button onClick={() => location.reload()}>重新载入</Button>
      </div>
    );
  }
}
