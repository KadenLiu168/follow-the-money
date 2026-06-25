import { describe, it, expect } from 'vitest';
import { mergeByIssuer } from '../../lib/feed/merge-by-issuer.js';

const a1 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 6.0, sharesOwned: 4000000, formType: 'SC 13D/A' };
const a2 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 6.8, sharesOwned: 4500000, formType: 'SC 13D/A' };
const b1 = { filerCik: 'B', issuerCik: 'Y', filingDate: '2026-06-20', ownershipPercent: 9.0, sharesOwned: 1000000, formType: 'SC 13D' };

describe('mergeByIssuer', () => {
  it('merges same (filer, issuer, day) into one with count', () => {
    const r = mergeByIssuer([a1, a2, b1]);
    expect(r).toHaveLength(2);
    const merged = r.find(g => g.issuerCik === 'X');
    expect(merged.count).toBe(2);
    expect(merged.ownershipPercent).toBe(6.8);
  });

  it('preserves groups with different days as separate', () => {
    const r = mergeByIssuer([a1, { ...a2, filingDate: '2026-06-21' }]);
    expect(r).toHaveLength(2);
  });
});
