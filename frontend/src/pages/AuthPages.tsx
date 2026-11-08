import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { Smartphone } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { api } from '../api/services';
import { ApiError } from '../api/client';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Field';
import { useAuthStore } from '../stores/auth';

const schema = z.object({
  phone: z.string().regex(/^1\d{10}$/, '请输入 11 位手机号'),
  code: z.string().length(6, '请输入 6 位验证码'),
});

type FormData = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const [sent, setSent] = useState(false);
  const { register, handleSubmit, getValues, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema), defaultValues: { phone: '13800000000', code: '123456' },
  });
  const send = useMutation({ mutationFn: () => api.sendSms(getValues('phone')), onSuccess: () => setSent(true) });
  const login = useMutation({
    mutationFn: (value: FormData) => api.login(value.phone, value.code),
    onSuccess: (session) => { setSession(session); navigate(params.get('next') || '/projects'); },
  });

  return (
    <div className="auth-page">
      <div className="auth-aside"><div className="auth-art"><span>24 × 24</span><div className="mini-grid" /></div><h1>保存每一次创作进度</h1><p>登录后可跨设备继续编辑和下载图纸。</p></div>
      <form className="auth-form" onSubmit={handleSubmit((value) => login.mutate(value))}>
        <span className="auth-icon"><Smartphone size={23} /></span>
        <h2>手机号登录</h2><p>未注册的手机号将自动创建账号</p>
        <Field label="手机号" error={errors.phone?.message}><Input inputMode="numeric" autoComplete="tel" {...register('phone')} /></Field>
        <Field label="验证码" error={errors.code?.message} hint="开发环境验证码为 123456">
          <div className="code-field"><Input inputMode="numeric" autoComplete="one-time-code" {...register('code')} /><Button type="button" variant="secondary" loading={send.isPending} onClick={() => send.mutate()}>{sent ? '已发送' : '获取验证码'}</Button></div>
        </Field>
        {(send.error || login.error) && <div className="inline-error">{(send.error || login.error)?.message}</div>}
        <Button className="full-button" type="submit" loading={login.isPending}>登录并继续</Button>
        <Link to="/" className="back-link">返回工作台</Link>
      </form>
    </div>
  );
}

export function AuthRequired({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (isAuthenticated) return children;
  return (
    <div className="auth-required">
      <span><Smartphone size={24} /></span><h1>登录后继续</h1><p>项目、服务权益和图纸版本需要绑定到你的账号。</p>
      <Link to={'/login?next=' + encodeURIComponent(location.pathname)}><Button>手机号登录</Button></Link>
    </div>
  );
}

export function ApiErrorCallout({ error }: { error: Error }) {
  const apiError = error instanceof ApiError ? error : null;
  return <div className="inline-error"><strong>{apiError?.code || 'REQUEST_FAILED'}</strong><span>{error.message}</span></div>;
}
