export function compute13FSummary(currentHoldings, priorHoldings = []) {
  const prior = new Map(priorHoldings.map(h => [h.cusip, h]));
  const curr = new Map(currentHoldings.map(h => [h.cusip, h]));

  const newPositions = [];
  const increasedPositions = currentHoldings.filter(h => {
    if (!prior.has(h.cusip)) { newPositions.push(h.cusip); return false; }
    return h.shares > prior.get(h.cusip).shares;
  }).length;
  const decreasedPositions = currentHoldings.filter(h => {
    const p = prior.get(h.cusip);
    return p && h.shares < p.shares;
  }).length;
  const closedPositions = [...prior.keys()].filter(c => !curr.has(c));

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
