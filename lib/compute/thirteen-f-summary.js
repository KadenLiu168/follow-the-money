export function compute13FSummary(currentHoldings, priorHoldings = []) {
  const prior = new Map(priorHoldings.map((h) => [h.cusip, h]));
  const curr = new Map(currentHoldings.map((h) => [h.cusip, h]));

  // Compute newPositions explicitly — no mutation inside a .filter() callback.
  const newPositions = [];
  for (const h of currentHoldings) {
    if (!prior.has(h.cusip)) newPositions.push(h.cusip);
  }
  const increasedPositions = currentHoldings.filter((h) => {
    const p = prior.get(h.cusip);
    return p && h.shares > p.shares;
  }).length;
  const decreasedPositions = currentHoldings.filter((h) => {
    const p = prior.get(h.cusip);
    return p && h.shares < p.shares;
  }).length;
  const closedPositions = [...prior.keys()].filter((c) => !curr.has(c));

  const totalValueUsd = currentHoldings.reduce((s, h) => s + (Number(h.valueUsd) || 0), 0);

  return {
    totalHoldingsCount: currentHoldings.length,
    totalValueUsd,
    newPositions,
    closedPositions,
    increasedPositions,
    decreasedPositions,
  };
}
