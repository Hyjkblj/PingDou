import { apiRequest } from './client';
import { mapProject, mapProjectDetail } from './mappers';
import type {
  Asset,
  AsyncJob,
  AuthSession,
  BaseImageVersion,
  ColorUsage,
  ExportJob,
  Order,
  Palette,
  PaletteColor,
  Pattern,
  Product,
  Project,
  ProjectList,
  RedemptionResult,
} from './types';

export const api = {
  sendSms: (phone: string) =>
    apiRequest<{ cooldownSeconds: number }>('/auth/sms/send', {
      method: 'POST',
      body: { phone, scene: 'LOGIN' },
    }),

  login: (phone: string, code: string) =>
    apiRequest<AuthSession>('/auth/sms/login', { method: 'POST', body: { phone, code } }),

  product: () => apiRequest<Product>('/products/current'),

  createOrder: (productId: string) =>
    apiRequest<Order>('/orders', {
      method: 'POST',
      body: { productId, channel: 'WECHAT_NATIVE' },
      idempotent: true,
    }),

  order: (orderId: string) => apiRequest<Order>('/orders/' + orderId),

  redeem: (code: string) =>
    apiRequest<RedemptionResult>('/redemption-codes/redeem', {
      method: 'POST',
      body: { code },
      idempotent: true,
    }),

  projects: async (query = ''): Promise<Project[]> => {
    const value = await apiRequest<ProjectList>('/projects?limit=30&query=' + encodeURIComponent(query));
    return value.items.map(mapProject);
  },

  project: async (id: string) => mapProjectDetail(await apiRequest('/projects/' + id)),

  createProject: async (name: string) =>
    mapProject(await apiRequest('/projects', { method: 'POST', body: { name } })),

  renameProject: async (id: string, name: string) =>
    mapProject(await apiRequest('/projects/' + id, { method: 'PATCH', body: { name } })),

  deleteProject: (id: string) => apiRequest<void>('/projects/' + id, { method: 'DELETE' }),

  uploadAsset: async (projectId: string, file: File, onProgress?: (value: number) => void) => {
    onProgress?.(10);
    const bytes = await file.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const sha256 = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
    const init = await apiRequest<{ uploadId: string; uploadUrl: string; headers: Record<string, string> }>(
      '/assets/upload-init',
      {
        method: 'POST',
        body: {
          projectId,
          fileName: file.name,
          mimeType: file.type,
          size: file.size,
          sha256,
          assetType: 'SOURCE_IMAGE',
        },
        idempotent: true,
      },
    );
    onProgress?.(45);
    let uploadUrl = init.uploadUrl;
    try {
      const parsed = new URL(init.uploadUrl, location.origin);
      if (parsed.pathname.startsWith('/api/v1/')) uploadUrl = parsed.pathname + parsed.search;
    } catch {
      // Relative URLs can be passed through unchanged.
    }
    await apiRequest<void>(uploadUrl, {
      method: 'PUT',
      body: new Blob([bytes], { type: file.type }),
      headers: init.headers,
    });
    onProgress?.(85);
    const asset = await apiRequest<Asset>('/assets/upload-complete', {
      method: 'POST',
      body: { uploadId: init.uploadId },
    });
    onProgress?.(100);
    return asset;
  },

  analyze: (projectId: string, sourceAssetId: string) =>
    apiRequest<AsyncJob>('/image-analysis/jobs', {
      method: 'POST', body: { projectId, sourceAssetId }, idempotent: true,
    }),

  removeBackground: (projectId: string, sourceAssetId: string, strength = 'STANDARD') =>
    apiRequest<AsyncJob>('/background-removal/jobs', {
      method: 'POST', body: { projectId, sourceAssetId, strength }, idempotent: true,
    }),

  job: (id: string) => apiRequest<AsyncJob>('/jobs/' + id),

  createPreview: (projectId: string, payload: Record<string, unknown>) =>
    apiRequest<any>('/projects/' + projectId + '/base-image-previews', { method: 'POST', body: payload }),

  confirmBase: (projectId: string, baseImagePreviewId: string) =>
    apiRequest<BaseImageVersion>('/projects/' + projectId + '/base-images/confirm', {
      method: 'POST', body: { baseImagePreviewId }, idempotent: true,
    }),

  generateAi: (payload: Record<string, unknown>) =>
    apiRequest<AsyncJob>('/ai-generation/jobs', {
      method: 'POST', body: payload, idempotent: true,
    }),

  palettes: () => apiRequest<Palette[]>('/palettes'),
  paletteColors: (id: string, version: string) =>
    apiRequest<PaletteColor[]>('/palettes/' + id + '/colors?version=' + encodeURIComponent(version)),

  generatePattern: (payload: Record<string, unknown>) =>
    apiRequest<AsyncJob>('/patterns/generation-jobs', {
      method: 'POST', body: payload, idempotent: true,
    }),

  pattern: async (id: string): Promise<Pattern> => {
    const raw = await apiRequest<any>('/patterns/' + id);
    if (Array.isArray(raw.matrix)) return raw as Pattern;
    const colors = await api.paletteColors(raw.paletteId, raw.paletteVersion);
    const index = new Map((raw.matrix.colorIndex || []).map((item: any) => [item.index, item.colorId]));
    const bytes = Uint8Array.from(atob(raw.matrix.data), (char) => char.charCodeAt(0));
    const flat: (string | null)[] = [];
    for (let offset = 0; offset < bytes.length; offset += 4) {
      const value = bytes[offset] * 256 + bytes[offset + 1];
      const run = bytes[offset + 2] * 256 + bytes[offset + 3];
      for (let count = 0; count < run; count += 1) flat.push(value === 0 ? null : (index.get(value) as string));
    }
    const matrix = Array.from({ length: raw.height }, (_, row) => flat.slice(row * raw.width, (row + 1) * raw.width));
    return {
      id: raw.id, projectId: raw.projectId, version: raw.version, width: raw.width, height: raw.height,
      beadSizeMm: raw.beadSizeMm, backgroundMode: raw.backgroundMode, matrix,
      lockedCells: [], palette: { id: raw.paletteId, version: raw.paletteVersion, colors },
      params: {}, score: raw.score || {}, matrixChecksum: raw.matrix.checksum,
    };
  },

  patchPattern: (id: string, payload: Record<string, unknown>) =>
    apiRequest<any>('/patterns/' + id + '/cells', {
      method: 'PATCH', body: payload, idempotent: true,
    }),

  colorUsage: async (id: string, version: number): Promise<ColorUsage> => {
    const raw = await apiRequest<any>('/patterns/' + id + '/color-usage?version=' + version);
    if (!Array.isArray(raw)) return raw as ColorUsage;
    const colors = raw.map((item: any) => ({
      colorId: item.colorId, code: item.code, name: item.name, rgb: item.rgb,
      count: item.netCount, countWithWaste: item.recommendedCount,
    }));
    return { totalBeads: colors.reduce((sum: number, item: any) => sum + item.count, 0), transparentCells: 0, colors };
  },

  exportPattern: (payload: Record<string, unknown>) =>
    apiRequest<ExportJob>('/export-jobs', { method: 'POST', body: payload, idempotent: true }),

  downloadExport: (exportId: string) =>
    apiRequest<Response>('/export-jobs/' + exportId + '/download', { raw: true }),
};
