export function filterByLookback(items, { lookbackDays, now = new Date() }) {
  if (!Number.isInteger(lookbackDays) || lookbackDays <= 0) throw new Error('lookbackDays must be > 0');
  const cutoff = new Date(now.getTime() - lookbackDays * 24 * 60 * 60 * 1000);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  return items.filter(it => it.filingDate >= cutoffStr);
}
