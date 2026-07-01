// Per-file valueUsd units detector.
//
// SEC EDGAR's 13F informationTable XML <value> field is officially in
// thousands of dollars (Form 13F DataFeed schema). In practice, observed
// feed-13f.json shows per-filer inconsistency: most filers emit raw dollars,
// a few (e.g. Baupost) emit thousands. This module infers the unit from
// portfolio magnitude and adjusts holdings.valueUsd accordingly.
//
// Heuristic:
//   - style: 'small-fund' in config → opt out, valueUnit = 'unknown', no change
//   - sum < $1B → assume thousands, ×1000, mark valueUnitAdjusted
//   - sum ≥ $1B → assume dollars, no change

const ONE_BILLION = 1_000_000_000;

export function normalizeValueUnits(filerEntry, configSources) {
  const entry = { ...filerEntry };
  const matchedSource = (configSources || []).find((s) => s.cik === entry.filerCik);
  const explicitlySmall = matchedSource?.style === 'small-fund';

  if (explicitlySmall) {
    return { ...entry, valueUnit: 'unknown' };
  }

  const sum = (entry.holdings || []).reduce((s, h) => s + (Number(h.valueUsd) || 0), 0);

  if (sum === 0 || sum >= ONE_BILLION) {
    return { ...entry, valueUnit: 'dollars' };
  }

  return {
    ...entry,
    valueUnit: 'thousands',
    valueUnitAdjusted: true,
    holdings: (entry.holdings || []).map((h) => ({ ...h, valueUsd: (Number(h.valueUsd) || 0) * 1000 })),
  };
}
