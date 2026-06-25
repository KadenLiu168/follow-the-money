import { describe, it, expect } from 'vitest';
import { filterByLookback } from '../../lib/feed/filter-by-lookback.js';

const NOW = new Date('2026-06-25T00:00:00Z');

describe('filterByLookback', () => {
  it('keeps only items within window', () => {
    const items = [
      { filingDate: '2026-06-24' },
      { filingDate: '2026-06-18' },
      { filingDate: '2026-06-17' },
    ];
    const r = filterByLookback(items, { lookbackDays: 7, now: NOW });
    expect(r).toHaveLength(2);
  });

  it('with lookbackDays=1 keeps today and yesterday (inclusive of now - lookbackDays)', () => {
    const r = filterByLookback([{ filingDate: '2026-06-25' }, { filingDate: '2026-06-24' }, { filingDate: '2026-06-23' }], { lookbackDays: 1, now: NOW });
    expect(r).toHaveLength(2);
  });
});
