import { delay, http, HttpResponse } from 'msw';
import { createMockPattern, mockColors, mockPatterns, mockProjects } from './fixtures';

const API = '*/api/v1';
const jobs = new Map<string, any>();
const assets = new Map<string, any>();
const uploads = new Map<string, any>();

const envelope = (data: any, status = 200) =>
  HttpResponse.json({ requestId: 'req_mock_' + crypto.randomUUID(), data, meta: null }, { status });

const error = (code: string, message: string, status: number, details?: Record<string, unknown>) =>
  HttpResponse.json(
    { requestId: 'req_mock', error: { code, message, retryable: false, details: details ?? null } },
    { status },
  );

const now = () => new Date().toISOString();
const newId = (prefix: string) => prefix + '-' + crypto.randomUUID();

function makeJob(type: string, result: Record<string, unknown>) {
  const id = newId('job');
  const job = {
    id, type, status: 'SUCCEEDED', progress: 100, stage: 'COMPLETED',
    createdAt: now(), updatedAt: now(), result, error: null,
  };
  jobs.set(id, job);
  return job;
}

export const handlers = [
  http.post(API + '/auth/sms/send', async () => {
    await delay(350);
    return envelope({ cooldownSeconds: 60 });
  }),

  http.post(API + '/auth/sms/login', async ({ request }) => {
    const body = await request.json() as any;
    await delay(450);
    if (body.code !== '123456') return error('SMS_CODE_INVALID', '验证码不正确，请输入 123456', 400);
    return envelope({
      accessToken: 'mock-access-token', refreshToken: 'mock-refresh-token', expiresIn: 7200,
      user: { id: 'user-mock-01', phoneMasked: body.phone.slice(0, 3) + '****' + body.phone.slice(-4) },
    });
  }),

  http.get(API + '/products/current', () => envelope({
    id: 'product-once', name: '单次拼豆图纸服务', priceCents: 1990, listPriceCents: 2990,
    currency: 'CNY', sourceAssetLimit: 1, aiCandidateCount: 2, editWindowHours: 72,
    downloadRetentionDays: 30, codeValidityDays: 365, exportFormats: ['PNG', 'PDF', 'CSV'],
    refundPolicyVersion: '2026.1',
  })),

  http.post(API + '/orders', async () => {
    await delay(400);
    const id = newId('order');
    return envelope({
      id, status: 'PENDING_PAYMENT', amountCents: 1990,
      payment: { channel: 'WECHAT_NATIVE', payload: { prepayId: 'mock-prepay' }, expiresAt: new Date(Date.now() + 900000).toISOString() },
    }, 201);
  }),

  http.get(API + '/orders/:orderId', ({ params }) => envelope({
    id: params.orderId, status: 'PAID', amountCents: 1990, paidAt: now(),
    redemptionCode: { code: 'PD-TEST-CODE-FOR-DEV', status: 'UNREDEEMED', expiresAt: new Date(Date.now() + 31536000000).toISOString() },
  })),

  http.post(API + '/redemption-codes/redeem', async ({ request }) => {
    const body = await request.json() as any;
    await delay(600);
    if (body.code === 'PD-USED-CODE') {
      return error('CODE_ALREADY_REDEEMED', '该业务码已兑换，可继续原项目', 409, { projectId: 'project-demo-01' });
    }
    if (body.code !== 'PD-TEST-CODE-FOR-DEV') return error('CODE_INVALID', '业务码无效，请核对后重试', 404);
    const project = {
      id: newId('project'), name: '新拼豆图纸', status: 'DRAFT', coverUrl: null,
      entitlementId: newId('ent'), latestPatternId: null, updatedAt: now(),
    };
    mockProjects.unshift(project);
    return envelope({
      redemptionCodeStatus: 'BOUND', project: { id: project.id, status: project.status },
      entitlement: {
        id: project.entitlementId, status: 'ACTIVE', sourceAssetLimit: 1,
        aiJobsTotal: 1, aiJobsUsed: 0, editExpiresAt: null, downloadExpiresAt: null,
      },
    }, 201);
  }),

  http.get(API + '/projects', ({ request }) => {
    const query = new URL(request.url).searchParams.get('query')?.toLowerCase() || '';
    return envelope({ items: mockProjects.filter((item) => item.name.toLowerCase().includes(query)), nextCursor: null });
  }),

  http.post(API + '/projects', async ({ request }) => {
    const body = await request.json() as any;
    const item = { id: newId('project'), name: body.name, status: 'DRAFT', coverUrl: null, entitlementId: null, latestPatternId: null, updatedAt: now() };
    mockProjects.unshift(item);
    return envelope(item, 201);
  }),

  http.get(API + '/projects/:projectId', ({ params }) => {
    const project = mockProjects.find((item) => item.id === params.projectId);
    if (!project) return error('PROJECT_NOT_FOUND', '项目不存在', 404);
    return envelope({
      ...project,
      sourceAssets: [...assets.values()].filter((asset) => asset.projectId === project.id),
      baseImageVersion: project.status === 'DRAFT' ? null : {
        id: 'base-' + project.id, projectId: project.id, sourceAssetId: 'asset-source',
        previewAsset: { previewUrl: '' }, backgroundMode: 'WHITE_PREVIEW', confirmedAt: now(),
      },
      pattern: project.latestPatternId ? mockPatterns.get(project.latestPatternId) : null,
      entitlement: project.entitlementId ? {
        id: project.entitlementId, status: 'ACTIVE', sourceAssetLimit: 1, aiJobsTotal: 1,
        aiJobsUsed: 0, editExpiresAt: new Date(Date.now() + 259200000).toISOString(),
        downloadExpiresAt: new Date(Date.now() + 2592000000).toISOString(),
      } : null,
    });
  }),

  http.patch(API + '/projects/:projectId', async ({ params, request }) => {
    const project = mockProjects.find((item) => item.id === params.projectId);
    if (!project) return error('PROJECT_NOT_FOUND', '项目不存在', 404);
    const body = await request.json() as any;
    Object.assign(project, body, { updatedAt: now() });
    return envelope(project);
  }),

  http.delete(API + '/projects/:projectId', ({ params }) => {
    const index = mockProjects.findIndex((item) => item.id === params.projectId);
    if (index >= 0) mockProjects.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(API + '/assets/upload-init', async ({ request }) => {
    const body = await request.json() as any;
    const uploadId = newId('upload');
    uploads.set(uploadId, body);
    return envelope({
      uploadId, method: 'PUT', uploadUrl: location.origin + '/api/v1/uploads/' + uploadId + '/content',
      headers: {}, expiresAt: new Date(Date.now() + 900000).toISOString(),
    }, 201);
  }),

  http.put(API + '/uploads/:uploadId/content', async ({ params, request }) => {
    const upload = uploads.get(params.uploadId as string);
    if (upload) upload.content = await request.arrayBuffer();
    await delay(500);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(API + '/assets/upload-complete', async ({ request }) => {
    const body = await request.json() as any;
    const upload = uploads.get(body.uploadId);
    if (!upload) return error('UPLOAD_NOT_FOUND', '上传任务不存在', 404);
    const id = newId('asset');
    const asset = {
      id, projectId: upload.projectId, type: 'SOURCE_IMAGE', fileName: upload.fileName,
      mimeType: upload.mimeType, size: upload.size, width: 1600, height: 1600,
      previewUrl: '', createdAt: now(),
    };
    assets.set(id, asset);
    return envelope(asset, 201);
  }),

  http.post(API + '/image-analysis/jobs', async () => {
    await delay(650);
    return envelope(makeJob('IMAGE_ANALYSIS', {
      qualityScore: 89, subjectType: 'PORTRAIT', backgroundComplexity: 'MEDIUM',
      recommendation: 'REMOVE_BACKGROUND', aiRecommended: true,
      reasons: ['主体清晰，适合保留轮廓', '背景细节较多，建议先抠图', '转为卡通风格可减少碎色'],
    }), 202);
  }),

  http.post(API + '/background-removal/jobs', async () => {
    await delay(600);
    const foregroundId = newId('foreground');
    const maskId = newId('mask');
    return envelope(makeJob('BACKGROUND_REMOVAL', {
      foregroundAssetId: foregroundId, maskAssetId: maskId, edgeQualityScore: 92,
    }), 202);
  }),

  http.get(API + '/jobs/:jobId', ({ params }) => {
    const job = jobs.get(params.jobId as string);
    return job ? envelope(job) : error('JOB_NOT_FOUND', '任务不存在', 404);
  }),

  http.post(API + '/ai-generation/jobs', async () => {
    await delay(750);
    return envelope(makeJob('AI_GENERATION', {
      candidates: [
        { assetId: 'candidate-01', score: 91, label: '轮廓清晰', recommended: true },
        { assetId: 'candidate-02', score: 83, label: '色彩柔和', recommended: false },
      ],
    }), 202);
  }),

  http.post(API + '/projects/:projectId/base-image-previews', async ({ params, request }) => {
    const body = await request.json() as any;
    return envelope({
      id: newId('preview'), projectId: params.projectId, previewAssetId: newId('asset-preview'),
      backgroundMode: body.background.mode, estimatedBackgroundBeadCount: body.background.mode.startsWith('SOLID_') ? 340 : 0,
    }, 201);
  }),

  http.post(API + '/projects/:projectId/base-images/confirm', async ({ params }) => {
    const project = mockProjects.find((item) => item.id === params.projectId);
    if (project) { project.status = 'PATTERN_PENDING'; project.updatedAt = now(); }
    return envelope({
      id: 'base-' + params.projectId, projectId: params.projectId, sourceAssetId: 'asset-source',
      foregroundAssetId: 'foreground', maskAssetId: 'mask', previewAsset: { id: 'preview-asset', previewUrl: '' },
      crop: { x: 0, y: 0, width: 1, height: 1, rotation: 0, flipX: false, flipY: false },
      backgroundMode: 'WHITE_PREVIEW', backgroundPaletteColorId: null, confirmedAt: now(),
    }, 201);
  }),

  http.get(API + '/palettes', () => envelope([{
    id: 'palette-pingdou', brand: 'PingDou', series: 'MVP', name: '拼豆基础色板',
    version: 'PINGDOU-2026.1', status: 'ACTIVE', colorCount: mockColors.length,
  }])),

  http.get(API + '/palettes/:paletteId/colors', () => envelope(mockColors)),

  http.post(API + '/patterns/generation-jobs', async ({ request }) => {
    const body = await request.json() as any;
    await delay(900);
    const patternId = newId('pattern');
    const pattern = createMockPattern(patternId, body.projectId, body.grid.width, body.grid.height);
    mockPatterns.set(patternId, pattern);
    const project = mockProjects.find((item) => item.id === body.projectId);
    if (project) { project.latestPatternId = patternId; project.status = 'EDITING'; project.updatedAt = now(); }
    return envelope(makeJob('PATTERN_GENERATION', { patternId, manufacturabilityScore: pattern.score }), 202);
  }),

  http.get(API + '/patterns/:patternId', ({ params }) => {
    const pattern = mockPatterns.get(params.patternId as string);
    return pattern ? envelope(pattern) : error('PATTERN_NOT_FOUND', '图纸不存在', 404);
  }),

  http.patch(API + '/patterns/:patternId/cells', async ({ params, request }) => {
    const pattern = mockPatterns.get(params.patternId as string);
    if (!pattern) return error('PATTERN_NOT_FOUND', '图纸不存在', 404);
    const body = await request.json() as any;
    if (body.patternVersion !== pattern.version) {
      return error('PATTERN_VERSION_CONFLICT', '图纸已在其他位置更新', 409, { currentVersion: pattern.version });
    }
    for (const change of body.changes) pattern.matrix[change.row][change.column] = change.toColorId;
    pattern.version += 1;
    pattern.matrixChecksum = 'mock-checksum-' + pattern.version;
    return envelope(pattern);
  }),

  http.get(API + '/patterns/:patternId/color-usage', ({ params }) => {
    const pattern = mockPatterns.get(params.patternId as string);
    if (!pattern) return error('PATTERN_NOT_FOUND', '图纸不存在', 404);
    const counts = new Map<string, number>();
    let transparentCells = 0;
    pattern.matrix.flat().forEach((id) => id ? counts.set(id, (counts.get(id) || 0) + 1) : transparentCells += 1);
    const colors = mockColors.filter((c) => counts.has(c.id)).map((c) => ({
      colorId: c.id, code: c.code, name: c.name, rgb: c.rgb,
      count: counts.get(c.id) || 0, countWithWaste: Math.ceil((counts.get(c.id) || 0) * 1.05),
    }));
    return envelope({ totalBeads: colors.reduce((sum, c) => sum + c.count, 0), transparentCells, colors });
  }),

  http.post(API + '/export-jobs', async ({ request }) => {
    const body = await request.json() as any;
    await delay(600);
    const content = encodeURIComponent('PingDou ' + body.format + ' export\nGenerated in mock mode.');
    return envelope({
      exportId: newId('export'), status: 'SUCCEEDED', format: body.format,
      fileName: 'pingdou-pattern.' + body.format.toLowerCase(), fileSize: 245760,
      pageCount: body.format === 'PDF' ? 3 : null,
      downloadUrl: 'data:text/plain;charset=utf-8,' + content,
      downloadUrlExpiresAt: new Date(Date.now() + 900000).toISOString(),
      retainedUntil: new Date(Date.now() + 2592000000).toISOString(),
    }, 202);
  }),
];
