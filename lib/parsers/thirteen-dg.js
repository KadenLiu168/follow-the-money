const INTENT_BY_FORM = {
  'SC 13D': 'active',
  'SC 13D/A': 'active',
  'SC 13G': 'passive',
  'SC 13G/A': 'passive',
};

function stripTags(html) {
  return html
    .replace(/<([A-Z][A-Z0-9 ]+)>/g, ' $1 ')
    // Preserve the close-tag name (e.g. </NAME> → " /NAME ") so SGML close
    // tags can act as value boundaries. The leading slash is the marker.
    .replace(/<\/([A-Z][A-Z0-9 ]+)>/g, ' /$1 ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&#\d+;/g, ' ')
    .replace(/&[a-z]+;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// 13D/G appears in two shapes on EDGAR:
//   SGML:   "<NAME OF ISSUER>Jet.AI Inc</NAME>" — value between matching open/close tags
//   HTML:   "Newegg Commerce, Inc. (Name of Issuer)" — value before the paren-wrapped label
// Try the SGML shape first (label.../label), then the HTML shape. First reasonable match wins.
function pickFirst(html, labels, stopLabels = []) {
  const text = stripTags(html);

  for (const label of labels) {
    // SGML shape: open label ... close tag (either same label or first word of label).
    // </AGGREGATE> for "AGGREGATE AMOUNT BENEFICIALLY OWNED", </NAME> for "NAME OF ISSUER".
    // After stripTags the close becomes " /AGGREGATE " or " /NAME ".
    const firstWord = label.split(/\s+/)[0];
    const closeLabels = [firstWord, ...stopLabels];
    // Build a "value... until close or stop label" pattern. We use a single
    // capture group with a stop that prefers the close tag.
    const sgmlRe = new RegExp(
      `\\b${label}\\b[:.,;()\\-\\s]+([A-Za-z0-9.,'\\-\\s]+?)(?=\\s*/\\s*(?:${closeLabels.join('|')})\\b|\\s*\\(|\\s*(?:${stopLabels.join('|')})\\b|$)`,
      'i'
    );
    let m = text.match(sgmlRe);
    if (m) {
      const v = m[1].trim().replace(/[,;\s]+$/, '');
      if (v.length > 0) return v;
    }

    // HTML shape: value sits immediately before the paren-wrapped label.
    const htmlRe = new RegExp(
      `([A-Z][A-Za-z0-9.,&'\\-\\s]{2,120}?)\\s*\\(\\s*${label}\\s*\\)`,
      'i'
    );
    m = text.match(htmlRe);
    if (m) {
      // Don't strip trailing "." — it's part of "Inc." / "Ltd." company suffixes.
      const v = m[1].trim()
        .replace(/\s*[,;]+\s*$/, '')
        .replace(/\s+\([^)]*\)\s*$/, '')
        .trim();
      if (v.length > 0 && v.length < 120) return v;
    }
  }
  return null;
}

export function parseThirteenDG(html, { formType }) {
  if (!INTENT_BY_FORM[formType]) throw new Error(`invalid formType: ${formType}`);
  const issuerName = pickFirst(html, ['NAME OF ISSUER', 'Name of Issuer'], ['TICKER', 'TRADING SYMBOL', 'CUSIP', 'PERCENT OF CLASS', 'SIC']);
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
