import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';

export function LoadingState({ label = '正在载入' }: { label?: string }) {
  return <div className="state-block"><div className="spinner" /><span>{label}</span></div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="state-block state-empty"><Inbox size={26} /><strong>{title}</strong><p>{description}</p>{action}</div>;
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="state-block state-error">
      <AlertTriangle size={26} />
      <strong>暂时无法加载</strong>
      <p>{error.message}</p>
      {onRetry && <Button variant="secondary" icon={<RefreshCw size={16} />} onClick={onRetry}>重新加载</Button>}
    </div>
  );
}
