// Period-over-period summary for a 13F filer entry.
//
// Finds the most recent prior filing for the same CIK, calls
// compute13FSummary, then reshapes the CUSIP-string outputs into
// rich object arrays (cusip + issuerName + shares + valueUsd) for
// renderer use, and adds priorTotalValueUsd + deltaPct.

import { compute13FSummary } from '../compute/thirteen-f-summary.js';

function findPriorEntry(filerEntry, allFilings) {
  const sameCik = (allFilings || []).filter(
    (e) =>
      e.filerCik === filerEntry.filerCik &&
      (e.periodOfReport || '') < (filerEntry.periodOfReport || ''),
  );
  sameCik.sort((a, b) => (b.periodOfReport || '').localeCompare(a.periodOfReport || ''));
  return sameCik[0] || null;
}

function lookupCusip(cusip, holdings) {
  return (holdings || []).find((h) => h.cusip === cusip) || null;
}

export function periodDiff(filerEntry, allFilings) {
  const priorEntry = findPriorEntry(filerEntry, allFilings);
  if (!priorEntry) {
    return { ...filerEntry, summary: null };
  }

  const raw = compute13FSummary(filerEntry.holdings || [], priorEntry.holdings || []);
  const currHoldings = filerEntry.holdings || [];
  const priorHoldings = priorEntry.holdings || [];

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
