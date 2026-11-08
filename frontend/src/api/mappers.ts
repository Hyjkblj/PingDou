import type { Project, ProjectDetail } from './types';

export function mapProject(dto: any): Project {
  return {
    id: dto.id,
    name: dto.name,
    status: dto.status,
    coverUrl: dto.coverUrl ?? null,
    entitlementId: dto.entitlementId ?? null,
    latestPatternId: dto.latestPatternId ?? null,
    updatedAt: dto.updatedAt,
  };
}

export function mapProjectDetail(dto: any): ProjectDetail {
  return {
    ...mapProject(dto),
    sourceAssets: dto.sourceAssets ?? [],
    baseImageVersion: dto.baseImageVersion ?? null,
    pattern: dto.pattern ?? null,
    entitlement: dto.entitlement ?? null,
  };
}
