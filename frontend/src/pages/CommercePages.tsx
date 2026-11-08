import { useMutation, useQuery } from '@tanstack/react-query';
import { Check, CheckCircle2, Copy, FileDown, Image, Palette, ShieldCheck, TicketCheck } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/services';
import { ApiError } from '../api/client';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Field';
import { LoadingState } from '../components/feedback/States';
import { formatMoney } from '../lib/utils';
import { useAuthStore } from '../stores/auth';
import { ApiErrorCallout, AuthRequired } from './AuthPages';

export function CheckoutPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const product = useQuery({ queryKey: ['product'], queryFn: api.product });
  const createOrder = useMutation({
    mutationFn: () => api.createOrder(product.data!.id),
    onSuccess: (order) => navigate('/orders/' + order.id),
  });
  if (product.isLoading) return <LoadingState label="正在读取服务信息" />;
  if (!product.data) return <div className="page-container">当前服务暂不可用</div>;
  const item = product.data;
  return (
    <div className="checkout-page page-container">
      <div className="checkout-main">
        <span className="eyebrow">单次服务</span><h1>{item.name}</h1>
        <p className="checkout-intro">一次下单获得一个业务码，兑换后为一张图片生成一套可编辑拼豆图纸。</p>
        <div className="service-includes">
          <div><Image size={20} /><span><strong>图片处理</strong><small>抠图、白底预览与基底确认</small></span><Check size={17} /></div>
          <div><Palette size={20} /><span><strong>AI 候选图</strong><small>{item.aiCandidateCount} 张卡通优化候选</small></span><Check size={17} /></div>
          <div><FileDown size={20} /><span><strong>完整交付</strong><small>{item.exportFormats.join(' / ')} 图纸与材料表</small></span><Check size={17} /></div>
        </div>
        <div className="policy-note"><ShieldCheck size={18} /><p>业务码兑换前可按退款规则处理；完成兑换并开始图片处理后，因数字服务已履行不支持无理由退款。</p></div>
      </div>
      <aside className="order-summary">
        <h2>订单摘要</h2><div className="summary-line"><span>单次图纸服务</span><strong>{formatMoney(item.priceCents)}</strong></div>
        <div className="summary-line muted"><span>原价</span><del>{formatMoney(item.listPriceCents)}</del></div>
        <div className="summary-total"><span>应付</span><strong>{formatMoney(item.priceCents)}</strong></div>
        <Button className="full-button" loading={createOrder.isPending} onClick={() => isAuthenticated ? createOrder.mutate() : navigate('/login?next=/checkout')}>{isAuthenticated ? '确认下单' : '登录后下单'}</Button>
        {createOrder.error && <ApiErrorCallout error={createOrder.error} />}
        <small>支付成功后，业务码有效期 {item.codeValidityDays} 天</small>
      </aside>
    </div>
  );
}

export function OrderPage() {
  const { orderId = '' } = useParams();
  const order = useQuery({ queryKey: ['order', orderId], queryFn: () => api.order(orderId), refetchInterval: (q) => q.state.data?.status === 'PENDING_PAYMENT' ? 2000 : false });
  const [copied, setCopied] = useState(false);
  if (!order.data) return <LoadingState label="正在确认支付结果" />;
  const code = order.data.redemptionCode?.code;
  return (
    <div className="result-page page-container">
      <span className="result-icon"><CheckCircle2 size={32} /></span><span className="eyebrow">支付成功</span><h1>你的业务码已生成</h1>
      <p>每个业务码仅能兑换一次图纸服务，请在开始制作前确认使用的账号。</p>
      <div className="code-display"><span>{code || '正在生成业务码'}</span>{code && <button title="复制业务码" onClick={() => { navigator.clipboard.writeText(code); setCopied(true); }}><Copy size={18} />{copied ? '已复制' : '复制'}</button>}</div>
      <div className="result-actions"><Link to={'/redeem?code=' + encodeURIComponent(code || '')}><Button icon={<TicketCheck size={18} />}>立即兑换</Button></Link><Link to="/projects"><Button variant="secondary">查看项目</Button></Link></div>
    </div>
  );
}

export function RedeemPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const initialCode = new URLSearchParams(location.search).get('code') || 'PD-TEST-CODE-FOR-DEV';
  const [code, setCode] = useState(initialCode);
  const redeem = useMutation({
    mutationFn: () => api.redeem(code.trim().toUpperCase()),
    onSuccess: (result) => navigate('/projects/' + result.project.id + '/analysis'),
  });
  if (!isAuthenticated) return <AuthRequired><span /></AuthRequired>;
  const redeemedProjectId = redeem.error instanceof ApiError && redeem.error.code === 'CODE_ALREADY_REDEEMED' ? redeem.error.details?.projectId as string : null;
  return (
    <div className="redeem-page page-container">
      <div className="redeem-copy"><span className="eyebrow">开始一张新图纸</span><h1>兑换业务码</h1><p>兑换后将创建专属项目，并绑定一次图片处理、图纸生成与导出权益。</p><div className="redeem-points"><span><CheckCircle2 size={18} />原图与项目一一绑定</span><span><CheckCircle2 size={18} />AI 优化失败不消耗权益</span><span><CheckCircle2 size={18} />确认基底后仍可编辑图纸</span></div></div>
      <div className="redeem-form">
        <span className="redeem-icon"><TicketCheck size={24} /></span><h2>输入业务码</h2>
        <Field label="业务码" hint="开发演示码：PD-TEST-CODE-FOR-DEV"><Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="PD-XXXX-XXXX-XXXX" /></Field>
        {redeem.error && <ApiErrorCallout error={redeem.error} />}
        {redeemedProjectId && <Link to={'/projects/' + redeemedProjectId + '/analysis'}><Button variant="secondary" className="full-button">继续原项目</Button></Link>}
        <Button className="full-button" loading={redeem.isPending} disabled={!code.trim()} onClick={() => redeem.mutate()}>确认兑换</Button>
        <Link className="text-link centered" to="/checkout">还没有业务码？购买单次服务</Link>
      </div>
    </div>
  );
}
