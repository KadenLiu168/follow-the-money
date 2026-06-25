import { describe, it, expect } from 'vitest';
import { compute13FSummary } from '../../lib/compute/thirteen-f-summary.js';

const aapl = { cusip: '037833100', issuerName: 'APPLE INC', shares: 300000000, valueUsd: 58200000000, votingAuthority: { sole: 300000000, shared: 0, none: 0 } };
const goog = { cusip: '02079K305', issuerName: 'ALPHABET INC', shares: 10000000, valueUsd: 17000000000, votingAuthority: { sole: 10000000, shared: 0, none: 0 } };

describe('compute13FSummary', () => {
  it('all new when no prior', () => {
    const r = compute13FSummary([aapl, goog], []);
    expect(r.newPositions).toEqual(['037833100', '02079K305']);
    expect(r.closedPositions).toEqual([]);
    expect(r.totalValueUsd).toBe(58200000000 + 17000000000);
  });

  it('detects increased / decreased / closed', () => {
    const prior = [
      { ...aapl, shares: 200000000, valueUsd: 38800000000 },
      { cusip: '999999999', issuerName: 'OLDCO', shares: 1, valueUsd: 1, votingAuthority: { sole: 1, shared: 0, none: 0 } },
    ];
    const r = compute13FSummary([aapl], prior);
    expect(r.newPositions).toEqual([]);
    expect(r.closedPositions).toEqual(['999999999']);
    expect(r.increasedPositions).toBe(1);
    expect(r.decreasedPositions).toBe(0);
  });
});
