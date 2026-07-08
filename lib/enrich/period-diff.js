// Period-over-period summary for a 13F filer entry.
//
// Finds the most recent prior filing for the same CIK, calls
// compute13FSummary, then reshapes the CUSIP-string outputs into
// rich object arrays (cusip + issuerName + shares + valueUsd) for
// renderer use, and adds priorTotalValueUsd + deltaPct.
//
// Defensive units normalization: prior entry is passed through
// normalizeValueUnits here. For a raw prior (no `valueUnitAdjusted`),
// it triggers the ×1000 to dollars; for an already-normalized prior
// (with `valueUnitAdjusted === true`) the function short-circuits on
// the input marker. Per the value-units-normalization spec, normalizeValueUnits
// is idempotent, so this defensive call is always safe. Current entry is
// the caller's responsibility — see scripts/prepare-digest.js for the
// canonical pre-normalization pass.

import { compute13FSummary } from '../compute/thirteen-f-summary.js';
import { normalizeValueUnits } from './normalize-value-units.js';

/**
 * @param {Object} filerEntry  Current period entry. Caller must pre-normalize units if needed.
 * @param {Array}  allFilings  All entries to search for prior period (heterogeneous units tolerated).
 * @param {Array}  [configSources=[]]  Filers config (with `cik` and optional `style: 'small-fund'`) for units detection.
 * @return {Object} filerEntry with attached summary: { newPositions, closedPositions, increasedPositions, decreasedPositions, totalValueUsd, priorTotalValueUsd, deltaPct }.
 */
export function periodDiff(filerEntry, allFilings, configSources = []) {
  const priorEntry = findPriorEntry(filerEntry, allFilings);
  if (!priorEntry) {
    return { ...filerEntry, summary: null };
  }

  // Defensive units normalization: prior entry's unit regime is uncontrolled by
  // periodDiff (it was reverse-looked-up). normalizeValueUnits idempotent — no-op
  // when prior is already normalized dollars or a small-fund style.
  const normalizedPrior = normalizeValueUnits(priorEntry, configSources);

  const raw = compute13FSummary(filerEntry.holdings || [], normalizedPrior.holdings || []);
  const currHoldings = filerEntry.holdings || [];
  const priorHoldings = normalizedPrior.holdings || [];

  const newPositions = raw.newPositions
    .map((cusip) => lookupCusip(cusip, currHoldings))
    .filter(Boolean)
    .map((h) => ({ cusip: h.cusip, issuerName: h.issuerName, shares: h.shares, valueUsd: h.valueUsd }));

  const closedPositions = raw.closedPositions
    .map((cusip) => lookupCusip(cusip, priorHoldings))
    .filter(Boolean)
    .map((h) => ({
      cusip: h.cusip,
      issuerName: h.issuerName,
      sharesAtClose: h.shares,
      valueUsdAtClose: h.valueUsd,
    }));

  const priorTotalValueUsd = priorHoldings.reduce((s, h) => s + (Number(h.valueUsd) || 0), 0);
  const deltaPct = priorTotalValueUsd === 0 ? 0 : (raw.totalValueUsd - priorTotalValueUsd) / priorTotalValueUsd;

  return {
    ...filerEntry,
    summary: {
      newPositions,
      closedPositions,
      increasedPositions: raw.increasedPositions,
      decreasedPositions: raw.decreasedPositions,
      totalValueUsd: raw.totalValueUsd,
      priorTotalValueUsd,
      deltaPct,
    },
  };
}

function findPriorEntry(filerEntry, allFilings) {
  const sameCik = (allFilings || []).filter(
    (e) =>
      e.filerCik === filerEntry.filerCik &&
      (e.periodOfReport || '') < (filerEntry.periodOfReport || ''),
  );
  sameCik.sort((a, b) => {
    const p = (b.periodOfReport || '').localeCompare(a.periodOfReport || '');
    return p !== 0 ? p : (b.latestFilingDate || '').localeCompare(a.latestFilingDate || '');
  });
  return sameCik[0] || null;
}

function lookupCusip(cusip, holdings) {
  return (holdings || []).find((h) => h.cusip === cusip) || null;
}