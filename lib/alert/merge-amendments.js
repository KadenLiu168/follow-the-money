function fmtPct(n) {
  return Number.isInteger(n) ? `${n}.0` : `${n}`;
}

export function mergeAmendmentsForAlert(groups) {
  return groups.map(g => {
    const amendments = g.amendments ?? [g];
    amendments.sort((a, b) => a.filingDate.localeCompare(b.filingDate));
    const first = amendments[0];
    const last = amendments[amendments.length - 1];
    const summary = amendments.length === 1
      ? `${fmtPct(last.ownershipPercent)}%`
      : `${amendments.length} 次修订，${fmtPct(first.ownershipPercent)}% → ${fmtPct(last.ownershipPercent)}%`;
    return { ...last, count: amendments.length, summary };
  });
}
