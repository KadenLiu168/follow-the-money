export function mergeByIssuer(entries) {
  const groups = new Map();
  for (const e of entries) {
    const key = `${e.filerCik}|${e.issuerCik}|${e.filingDate}`;
    const prev = groups.get(key);
    if (!prev) {
      groups.set(key, { ...e, count: 1, amendments: [e] });
    } else {
      prev.amendments.push(e);
      prev.count = prev.amendments.length;
      // Latest by filingDate is the same day here; if ties, last wins
      if (e.ownershipPercent != null) prev.ownershipPercent = e.ownershipPercent;
      if (e.sharesOwned != null) prev.sharesOwned = e.sharesOwned;
    }
  }
  return [...groups.values()];
}
