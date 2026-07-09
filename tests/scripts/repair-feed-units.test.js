import { describe, it, expect } from 'vitest';
import { repairFeed, isDollarStored, DOLLARS_THRESHOLD } from '../../scripts/repair-feed-units.js';

// Fixture: 2 snapshots, mixed units.
//   A: stored in DOLLARS (max holding raw = 86.8e9 >= 1e9)
//   B: stored in THOUSANDS (max holding raw = 2.9e7 < 1e9)
const mixedFeed = {
  schemaVersion: 1,
  thirteenF: [
    {
      filerCik: '0001067983',
      filerName: 'Berkshire (dollar-stored)',
      periodOfReport: '2022-12-31',
      holdings: [
        { cusip: '037833100', issuerName: 'APPLE INC', valueUsd: 86841000000, shares: 100 },
        { cusip: '02079K107', issuerName: 'ALPHABET INC', valueUsd: 5000000000, shares: 50 },
      ],
      summary: { totalHoldingsCount: 2, totalValueUsd: 91841000000, newPositions: [], closedPositions: [], increasedPositions: 0, decreasedPositions: 0 },
    },
    {
      filerCik: '0001067983',
      filerName: 'Berkshire (thousands-stored)',
      periodOfReport: '2016-09-30',
      holdings: [
        { cusip: '037833100', issuerName: 'APPLE INC', valueUsd: 29000000, shares: 100 },
      ],
      summary: { totalHoldingsCount: 1, totalValueUsd: 29000000, newPositions: [], closedPositions: [], increasedPositions: 0, decreasedPositions: 0 },
    },
  ],
  stats: { thirteenFFilings: 2, thirteenFHoldings: 3 },
};

describe('repairFeed', () => {
  it('isDollarStored detects via max holding raw >= 1e9', () => {
    expect(isDollarStored(mixedFeed.thirteenF[0].holdings)).toBe(true);
    expect(isDollarStored(mixedFeed.thirteenF[1].holdings)).toBe(false);
    expect(DOLLARS_THRESHOLD).toBe(1e9);
  });

  it('normalizes dollar-stored snapshots to thousands and stamps marker', () => {
    const { feed, converted } = repairFeed(mixedFeed);
    expect(converted).toBe(1);
    const dollar = feed.thirteenF[0];
    expect(dollar.holdings[0].valueUsd).toBe(86841000000 / 1000);
    expect(dollar.holdings[1].valueUsd).toBe(5000000000 / 1000);
    expect(dollar.summary.totalValueUsd).toBe(91841000000 / 1000);
    expect(dollar.valueUnit).toBe('thousands');
    // legacy ambiguity cleared
    expect(dollar.valueUnitAdjusted).toBeUndefined();
  });

  it('leaves already-thousands snapshots unchanged but stamps marker', () => {
    const { feed } = repairFeed(mixedFeed);
    const thousands = feed.thirteenF[1];
    expect(thousands.holdings[0].valueUsd).toBe(29000000);
    expect(thousands.summary.totalValueUsd).toBe(29000000);
    expect(thousands.valueUnit).toBe('thousands');
  });

  it('is idempotent: re-running converts 0 and preserves values', () => {
    const first = repairFeed(mixedFeed);
    const second = repairFeed(first.feed);
    expect(second.converted).toBe(0);
    const dollar = second.feed.thirteenF[0];
    // values must not be divided a second time
    expect(dollar.holdings[0].valueUsd).toBe(86841000000 / 1000);
    expect(dollar.summary.totalValueUsd).toBe(91841000000 / 1000);
  });

  it('clears legacy valueUnitAdjusted if present on input', () => {
    const feedWithLegacy = {
      ...mixedFeed,
      thirteenF: [{
        ...mixedFeed.thirteenF[0],
        valueUnitAdjusted: true,
      }],
    };
    const { feed } = repairFeed(feedWithLegacy);
    expect(feed.thirteenF[0].valueUnitAdjusted).toBeUndefined();
    expect(feed.thirteenF[0].valueUnit).toBe('thousands');
  });
});
