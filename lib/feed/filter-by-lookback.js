export function filterByLookback(items, { lookbackDays, now = new Date(), field = 'filingDate' }) {
  if (!Number.isInteger(lookbackDays) || lookbackDays <= 0) throw new Error('lookbackDays must be > 0');
  const cutoff = new Date(now.getTime() - lookbackDays * 24 * 60 * 60 * 1000);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  // `field` lets callers window on a different date field (13F entries expose
  // `latestFilingDate`, not `filingDate`). Default preserves existing behavior.
  return items.filter(it => it[field] >= cutoffStr);
}
