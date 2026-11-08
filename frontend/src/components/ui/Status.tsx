import { Check, Clock3, CircleAlert, LoaderCircle } from 'lucide-react';

const statusLabels: Record<string, string> = {
  DRAFT: '待上传', ANALYZING: '分析中', BASE_IMAGE_PENDING: '待定基底', PATTERN_PENDING: '待生成',
  EDITING: '编辑中', COMPLETED: '已完成', ACTIVE: '服务中', AVAILABLE: '可使用',
  SUCCEEDED: '已完成', RUNNING: '处理中', QUEUED: '排队中', FAILED: '失败',
  PENDING_PAYMENT: '待支付', PAID: '已支付', BOUND: '已绑定',
};

export function StatusBadge({ status }: { status: string }) {
  const tone = ['COMPLETED', 'SUCCEEDED', 'PAID', 'ACTIVE'].includes(status)
    ? 'success'
    : ['FAILED', 'VOIDED'].includes(status) ? 'danger' : ['RUNNING', 'ANALYZING'].includes(status) ? 'info' : 'neutral';
  const Icon = tone === 'success' ? Check : tone === 'danger' ? CircleAlert : tone === 'info' ? LoaderCircle : Clock3;
  return <span className={'status status-' + tone}><Icon size={13} />{statusLabels[status] || status}</span>;
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  return (
    <div className="progress-wrap" aria-label={label || '任务进度'}>
      <div className="progress-meta"><span>{label || '处理中'}</span><strong>{value}%</strong></div>
      <div className="progress-track"><span style={{ width: value + '%' }} /></div>
    </div>
  );
}
