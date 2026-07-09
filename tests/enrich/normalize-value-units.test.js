import { describe, it, expect } from 'vitest';
import { normalizeValueUnits } from '../../lib/enrich/normalize-value-units.js';

// Config-driven model: unit comes from each source's `valueUnit`, not from
// portfolio magnitude. See openspec/specs/value-units-normalization.
const cfg = [
  { cik: '0001067983', name: 'Berkshire Hathaway Inc', style: 'value', valueUnit: 'thousands' },
  { cik: '0001061768', name: 'Baupost Group', style: 'value', valueUnit: 'thousands' },
  {
    cik: '0001649339',
    name: 'Scion Asset Management, LLC',
    style: 'deep-value',
    valueUnit: 'thousands',
  },
  { cik: '0000000099', name: 'Tiny Tagged Fund', style: 'small-fund' },
  { cik: '0001111111', name: 'Dollar Fund', style: 'value', valueUnit: 'dollars' },
];

const makeHolding = (cusip, shares, valueUsd) => ({
  cusip,
  issuerName: 'X',
  shares,
  valueUsd,
  votingAuthority: { sole: shares, shared: 0, none: 0 },
});

const makeEntry = (cik, name, holdings) => ({
  filerCik: cik,
  filerName: name,
  periodOfReport: '2026-03-31',
  latestFilingDate: '2026-05-15',
  latestFormType: '13F-HR',
  latestAccessionNumber: '0000000000-00-000000',
  holdings,
});

describe('normalizeValueUnits', () => {
  it('multiplies by 1000 when source declares thousands', () => {
    const entry = makeEntry('0001061768', 'Baupost Group', [
      makeHolding('1', 3118754, 649543),
      makeHolding('2', 8080112, 597208),
    ]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings[0].valueUsd).toBe(649543 * 1000);
    expect(out.holdings[1].valueUsd).toBe(597208 * 1000);
  });

  it('leaves valueUsd unchanged when source declares dollars', () => {
    const entry = makeEntry('0001111111', 'Dollar Fund', [makeHolding('1', 100000, 50000000)]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('dollars');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings[0].valueUsd).toBe(50000000);
  });

  it('defaults to thousands for an unmatched CIK (SEC 13F spec)', () => {
    const entry = makeEntry('9999999999', 'Unknown Filer', [makeHolding('1', 100000, 50000000)]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings[0].valueUsd).toBe(50000000 * 1000);
  });

  it('respects style: small-fund opt-out', () => {
    const entry = makeEntry('0000000099', 'Tiny Tagged Fund', [makeHolding('1', 100000, 50000000)]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('unknown');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings[0].valueUsd).toBe(50000000);
  });

  it('handles empty holdings array (thousands source)', () => {
    const entry = makeEntry('0001067983', 'Berkshire Hathaway Inc', []);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings).toEqual([]);
  });

  it('handles empty holdings array (dollars source)', () => {
    const entry = makeEntry('0001111111', 'Dollar Fund', []);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('dollars');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings).toEqual([]);
  });

  it('keeps already-normalized thousands entry unchanged (idempotency)', () => {
    const entry = makeEntry('0001067983', 'Berkshire Hathaway Inc', [
      makeHolding('1', 100000, 200000),
      makeHolding('2', 200000, 300000),
    ]);
    const firstPass = normalizeValueUnits(entry, cfg);
    expect(firstPass.valueUnit).toBe('thousands');
    expect(firstPass.valueUnitAdjusted).toBe(true);
    expect(firstPass.holdings[0].valueUsd).toBe(200000 * 1000);
    expect(firstPass.holdings[1].valueUsd).toBe(300000 * 1000);

    const secondPass = normalizeValueUnits(firstPass, cfg);
    expect(secondPass.valueUnit).toBe('thousands');
    expect(secondPass.valueUnitAdjusted).toBe(true);
    expect(secondPass.holdings[0].valueUsd).toBe(200000 * 1000);
    expect(secondPass.holdings[1].valueUsd).toBe(300000 * 1000);
  });

  it('keeps already-normalized dollars entry unchanged (idempotency)', () => {
    const entry = makeEntry('0001111111', 'Dollar Fund', [makeHolding('1', 100000, 200000)]);
    const firstPass = normalizeValueUnits(entry, cfg);
    expect(firstPass.valueUnit).toBe('dollars');
    expect(firstPass.valueUnitAdjusted).toBeUndefined();
    expect(firstPass.holdings[0].valueUsd).toBe(200000);

    const secondPass = normalizeValueUnits(firstPass, cfg);
    expect(secondPass.valueUnit).toBe('dollars');
    expect(secondPass.holdings[0].valueUsd).toBe(200000);
  });

  // --- repair-feed-units: entry marker takes precedence over config ---

  it('prefers entry marker thousands over config dollars', () => {
    // Entry declares thousands but its config source says dollars.
    const entry = makeEntry('0001111111', 'Dollar Fund', [makeHolding('1', 100000, 50000000)]);
    entry.valueUnit = 'thousands';
    const out = normalizeValueUnits(entry, cfg);
    // Marker wins: resolved as thousands, so ×1000 applies.
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings[0].valueUsd).toBe(50000000 * 1000);
  });

  it('prefers entry marker dollars over config thousands', () => {
    // Entry declares dollars but its config source says thousands.
    const entry = makeEntry('0001067983', 'Berkshire Hathaway Inc', [
      makeHolding('1', 100000, 200000000),
    ]);
    entry.valueUnit = 'dollars';
    const out = normalizeValueUnits(entry, cfg);
    // Marker wins: resolved as dollars, so holdings left unchanged.
    expect(out.valueUnit).toBe('dollars');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings[0].valueUsd).toBe(200000000);
  });

  it('falls back to config when entry marker is absent', () => {
    const entry = makeEntry('0001061768', 'Baupost Group', [makeHolding('1', 3118754, 649543)]);
    // No valueUnit on entry → config (thousands) applies.
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings[0].valueUsd).toBe(649543 * 1000);
  });
});
