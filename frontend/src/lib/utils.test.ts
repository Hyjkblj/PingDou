import { describe, expect, it } from 'vitest';
import { formatMoney, uid } from './utils';

describe('format helpers', () => {
  it('formats API cents as CNY', () => {
    expect(formatMoney(1990)).toContain('19.90');
  });

  it('creates namespaced operation ids', () => {
    expect(uid('operation')).toMatch(/^operation_[0-9a-f-]{36}$/);
  });
});
