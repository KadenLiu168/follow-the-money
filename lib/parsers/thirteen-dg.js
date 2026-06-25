const INTENT_BY_FORM = {
  'SC 13D': 'active',
  'SC 13D/A': 'active',
  'SC 13G': 'passive',
  'SC 13G/A': 'passive',
};

function stripTags(html) {
  return html
    .replace(/<([A-Z][A-Z0-9 ]*)>/g, ' $1 ')
    .replace(/<\/[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function pickFirst(html, labels, stopLabels = []) {
  const text = stripTags(html);
  const stops = stopLabels.length
    ? `(?=\\s+(?:${stopLabels.join('|')})\\s|$)`
    : '(?=\\s+[A-Z][A-Z ]*\\s+\\S|$)';
  for (const label of labels) {
    const re = new RegExp(`${label}\\s*[:\\-]?\\s*(.+?)${stops}`, 'i');
    const m = text.match(re);
    if (m) return m[1].trim();
  }
  return null;
}

export function parseThirteenDG(html, { formType }) {
  if (!INTENT_BY_FORM[formType]) throw new Error(`invalid formType: ${formType}`);
  const issuerName = pickFirst(html, ['NAME OF ISSUER'], ['TICKER', 'TRADING SYMBOL', 'CUSIP', 'PERCENT OF CLASS']);
  const ticker = pickFirst(html, ['TICKER', 'TRADING SYMBOL'], ['CUSIP', 'PERCENT OF CLASS', 'SHARED VOTING POWER', 'SOLE VOTING POWER', 'AGGREGATE AMOUNT BENEFICIALLY OWNED']);
  const percent = Number(pickFirst(html, ['PERCENT OF CLASS'], ['SHARED VOTING POWER', 'SOLE VOTING POWER', 'AGGREGATE AMOUNT BENEFICIALLY OWNED']) || '0');
  const shares = Number((pickFirst(html, ['AGGREGATE AMOUNT BENEFICIALLY OWNED']) || '0').replace(/,/g, ''));
  return {
    issuerName: issuerName || 'UNKNOWN',
    issuerTicker: ticker || '',
    ownershipPercent: percent,
    sharesOwned: shares,
    intent: INTENT_BY_FORM[formType],
  };
}
