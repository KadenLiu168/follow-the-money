import { describe, it, expect } from 'vitest';
import { mergeAmendmentsForAlert } from '../../lib/alert/merge-amendments.js';
import { mergeByIssuer } from '../../lib/feed/merge-by-issuer.js';

const e1 = {
  filerCik: 'A',
  issuerCik: 'X',
  filingDate: '2026-06-20',
  ownershipPercent: 5.1,
  sharesOwned: 4000000,
  formType: 'SC 13D/A',
};
const e2 = {
  filerCik: 'A',
  issuerCik: 'X',
  filingDate: '2026-06-20',
  ownershipPercent: 6.8,
  sharesOwned: 4500000,
  formType: 'SC 13D/A',
};
const e3 = {
  filerCik: 'A',
  issuerCik: 'X',
  filingDate: '2026-06-20',
  ownershipPercent: 7.0,
  sharesOwned: 4600000,
  formType: 'SC 13D/A',
};

describe('mergeAmendmentsForAlert', () => {
  it('produces count and summary across amendments in same group', () => {
    const groups = mergeByIssuer([e1, e2, e3]);
    const r = mergeAmendmentsForAlert(groups);
    expect(r).toHaveLength(1);
    expect(r[0].count).toBe(3);
    expect(r[0].summary).toBe('3 次修订，5.1% → 7.0%');
  });

  it('count=1 produces no arrow', () => {
    const groups = mergeByIssuer([e2]);
    const r = mergeAmendmentsForAlert(groups);
    expect(r[0].count).toBe(1);
    expect(r[0].summary).toBe('6.8%');
  });
});
