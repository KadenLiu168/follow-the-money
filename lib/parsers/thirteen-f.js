// SEC 13F informationTable XML -> normalized holdings.
// Zero runtime deps: regex on the flat per-holding block.
//
// Some filers (e.g. Baupost) emit namespaced XML like
//   <ns1:informationTable xmlns:ns1="..."><ns1:infoTable>...
// while most emit plain <informationTable><infoTable>. We strip the
// `xmlns:*` declarations and the `<prefix>:` prefix on tags so the same
// regex works for both.

function stripNamespaces(xml) {
  // Drop xmlns:* attribute declarations.
  let out = xml.replace(/\s+xmlns(:[a-zA-Z0-9]+)?="[^"]*"/g, '');
  // Drop `prefix:` from any opening, closing, or self-closing tag, keeping the `>`.
  out = out.replace(/<(\/?)([a-zA-Z0-9_]+):([a-zA-Z0-9_]+)([\s/>])/g, '<$1$3$4');
  return out;
}

function pickTag(block, tag) {
  const re = new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`);
  const m = block.match(re);
  return m ? m[1].trim() : '';
}

function pickInt(s) {
  return Number(String(s).replace(/,/g, '')) || 0;
}

export function parseThirteenF(xml) {
  const cleaned = stripNamespaces(xml);
  const holdings = [];
  const blockRe = /<infoTable>([\s\S]*?)<\/infoTable>/g;
  let m;
  while ((m = blockRe.exec(cleaned)) !== null) {
    const block = m[1];
    const inner = block.match(/<shrsOrPrnAmt>([\s\S]*?)<\/shrsOrPrnAmt>/);
    const shares = inner ? pickInt(pickTag(inner[1], 'sshPrnamt')) : 0;
    holdings.push({
      cusip: pickTag(block, 'cusip'),
      issuerName: pickTag(block, 'nameOfIssuer'),
      shares,
      valueUsd: pickInt(pickTag(block, 'value')),
      votingAuthority: {
        sole: pickInt(pickTag(block, 'Sole')),
        shared: pickInt(pickTag(block, 'Shared')),
        none: pickInt(pickTag(block, 'None')),
      },
    });
  }
  return holdings;
}
