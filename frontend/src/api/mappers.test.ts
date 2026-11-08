import { describe, expect, it } from 'vitest';
import { mapProject, mapProjectDetail } from './mappers';

describe('project mappers', () => {
  it('normalizes nullable summary fields', () => {
    expect(mapProject({
      id: 'project-1',
      name: '测试项目',
      status: 'DRAFT',
      updatedAt: '2026-08-04T08:00:00Z',
    })).toEqual({
      id: 'project-1',
      name: '测试项目',
      status: 'DRAFT',
      coverUrl: null,
      entitlementId: null,
      latestPatternId: null,
      updatedAt: '2026-08-04T08:00:00Z',
    });
  });

  it('creates independent detail collections', () => {
    const detail = mapProjectDetail({
      id: 'project-2',
      name: '图纸项目',
      status: 'EDITING',
      updatedAt: '2026-08-04T09:00:00Z',
      sourceAssets: [{ id: 'asset-1' }],
      pattern: { id: 'pattern-1' },
    });
    expect(detail.sourceAssets).toHaveLength(1);
    expect(detail.pattern).toEqual({ id: 'pattern-1' });
    expect(detail.entitlement).toBeNull();
  });
});
