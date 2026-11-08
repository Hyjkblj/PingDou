import type { ApiEnvelope, ApiErrorBody } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public retryable = false,
    public details?: Record<string, unknown> | null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
  idempotent?: boolean;
  raw?: boolean;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = localStorage.getItem('pingdou_access_token');
  const requestId = crypto.randomUUID();

  headers.set('X-Request-ID', requestId);
  if (token) headers.set('Authorization', 'Bearer ' + token);
  if (options.body !== undefined && !(options.body instanceof Blob)) {
    headers.set('Content-Type', 'application/json');
  }
  if (options.idempotent) headers.set('Idempotency-Key', crypto.randomUUID());

  let response: Response;
  try {
    const url = /^(https?:|data:|blob:)/.test(path) || path.startsWith(API_BASE) ? path : API_BASE + path;
    response = await fetch(url, {
      ...options,
      headers,
      body:
        options.body === undefined
          ? undefined
          : options.body instanceof Blob
            ? options.body
            : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError('NETWORK_ERROR', '网络连接不可用，请检查连接后重试', 0, true);
  }

  if (!response.ok) {
    let errorBody: ApiErrorBody | undefined;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = undefined;
    }
    throw new ApiError(
      errorBody?.error?.code || 'HTTP_ERROR',
      errorBody?.error?.message || '请求未能完成',
      response.status,
      errorBody?.error?.retryable || false,
      errorBody?.error?.details,
    );
  }

  if (response.status === 204) return undefined as T;
  if (options.raw) return response as T;
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}
