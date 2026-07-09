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
//
// Marker priority: a feed entry may declare its own `valueUnit` marker
// (stamped by the repair / feed-writer). When present it is authoritative
// and the config is only a fallback. This makes self-describing feeds
// win over a global config guess and prevents recurrence of mixed-unit debt.

const VALID_UNITS = new Set(['thousands', 'dollars']);

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

  // Prefer the entry's own declared marker when valid; config is fallback.
  const declared = VALID_UNITS.has(entry.valueUnit) ? entry.valueUnit : null;
  const unit = declared ?? matchedSource?.valueUnit ?? 'thousands';

  if (unit === 'dollars') {
    return { ...entry, valueUnit: 'dollars' };
  }

  // default: thousands (SEC 13F spec, and fallback for unmatched CIK)
  return {
    ...entry,
    valueUnit: 'thousands',
    valueUnitAdjusted: true,
    holdings: (entry.holdings || []).map((h) => ({
      ...h,
      valueUsd: (Number(h.valueUsd) || 0) * 1000,
    })),
  };
}
