export type ApiEnvelope<T> = {
  requestId: string;
  data: T;
  meta?: { nextCursor?: string | null; hasMore?: boolean } | null;
};

export type ApiErrorBody = {
  requestId?: string;
  error?: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Record<string, unknown> | null;
  };
};

export type User = { id: string; phoneMasked: string };

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: User;
};

export type Product = {
  id: string;
  name: string;
  priceCents: number;
  listPriceCents: number;
  currency: string;
  sourceAssetLimit: number;
  aiCandidateCount: number;
  editWindowHours: number;
  downloadRetentionDays: number;
  codeValidityDays: number;
  exportFormats: string[];
  refundPolicyVersion: string;
};

export type Order = {
  id: string;
  status: 'PENDING_PAYMENT' | 'PAID' | 'CLOSED' | 'REFUNDED';
  amountCents: number;
  paidAt?: string | null;
  payment?: {
    channel: string;
    payload: { prepayId?: string | null };
    expiresAt: string;
  };
  redemptionCode?: {
    code?: string | null;
    maskedCode?: string | null;
    status: string;
    expiresAt: string;
  } | null;
};

export type Entitlement = {
  id: string;
  status: string;
  sourceAssetLimit: number;
  aiJobsTotal: number;
  aiJobsUsed: number;
  editExpiresAt?: string | null;
  downloadExpiresAt?: string | null;
};

export type Project = {
  id: string;
  name: string;
  status: string;
  coverUrl?: string | null;
  entitlementId?: string | null;
  latestPatternId?: string | null;
  updatedAt: string;
};

export type ProjectDetail = Project & {
  sourceAssets: Asset[];
  baseImageVersion?: BaseImageVersion | null;
  pattern?: Pattern | null;
  entitlement?: Entitlement | null;
};

export type ProjectList = { items: Project[]; nextCursor?: string | null };

export type RedemptionResult = {
  redemptionCodeStatus: string;
  project: { id: string; status: string };
  entitlement: Entitlement;
};

export type Asset = {
  id: string;
  type: string;
  fileName: string;
  mimeType: string;
  size: number;
  width: number;
  height: number;
  previewUrl: string;
  createdAt: string;
};

export type AsyncJob = {
  id: string;
  type: string;
  status: 'QUEUED' | 'RUNNING' | 'REVIEWING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';
  progress: number;
  stage?: string | null;
  createdAt: string;
  updatedAt: string;
  result?: Record<string, any> | null;
  error?: { code: string; message: string; retryable: boolean } | null;
};

export type Palette = {
  id: string;
  brand: string;
  series: string;
  name: string;
  version: string;
  status: string;
  colorCount: number;
};

export type PaletteColor = {
  id: string;
  code: string;
  name: string;
  rgb: string;
  lab: number[];
  attributes: string[];
  enabled: boolean;
};

export type BaseImageVersion = {
  id: string;
  projectId: string;
  sourceAssetId: string;
  foregroundAssetId?: string | null;
  maskAssetId?: string | null;
  previewAsset: Asset;
  crop: Record<string, number | boolean>;
  backgroundMode: string;
  backgroundPaletteColorId?: string | null;
  confirmedAt: string;
};

export type Pattern = {
  id: string;
  projectId: string;
  version: number;
  width: number;
  height: number;
  beadSizeMm: number;
  backgroundMode: string;
  matrix: (string | null)[][];
  lockedCells: string[];
  palette: { id: string; version: string; colors: PaletteColor[] };
  params: Record<string, any>;
  score: Record<string, number | string>;
  matrixChecksum: string;
};

export type ColorUsage = {
  totalBeads: number;
  transparentCells: number;
  colors: Array<{
    colorId: string;
    code: string;
    name: string;
    rgb: string;
    count: number;
    countWithWaste: number;
  }>;
};

export type ExportJob = {
  exportId: string;
  status: string;
  format: string;
  fileName?: string | null;
  fileSize?: number | null;
  pageCount?: number | null;
  downloadUrl?: string | null;
  downloadUrlExpiresAt?: string | null;
  retainedUntil?: string | null;
};
