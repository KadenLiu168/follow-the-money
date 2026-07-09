// 13F value-unit resolution.
//
// SEC EDGAR's 13F informationTable XML <value> field is officially expressed
// in thousands of dollars (Form 13F DataFeed schema). Each filer's unit is
// declared explicitly in config/default-sources.json via `valueUnit`:
//   - 'thousands' → multiply holdings.valueUsd by 1000, set valueUnitAdjusted
//   - 'dollars'   → leave holdings.valueUsd unchanged
//   - 'small-fund' style → opt out, valueUnit = 'unknown', no change
//   - unmatched CIK → default to 'thousands' (SEC 13F spec)
//
// Idempotent: an entry already processed (valueUnitAdjusted === true) is
// returned unchanged. See openspec/specs/value-units-normalization.

export function normalizeValueUnits(filerEntry, configSources) {
  const entry = { ...filerEntry };
  const matchedSource = (configSources || []).find((s) => s.cik === entry.filerCik);
  const explicitlySmall = matchedSource?.style === 'small-fund';

  if (explicitlySmall) {
    return { ...entry, valueUnit: 'unknown' };
  }

  // Idempotency guard: honor valueUnitAdjusted on input to prevent re-multiplication.
  if (entry.valueUnitAdjusted === true) {
    return entry;
  }

  const unit = matchedSource?.valueUnit ?? 'thousands';

  if (unit === 'dollars') {
    return { ...entry, valueUnit: 'dollars' };
  }

  // default: thousands (SEC 13F spec, and fallback for unmatched CIK)
  return {
    ...entry,
    valueUnit: 'thousands',
    valueUnitAdjusted: true,
    holdings: (entry.holdings || []).map((h) => ({ ...h, valueUsd: (Number(h.valueUsd) || 0) * 1000 })),
  };
}
