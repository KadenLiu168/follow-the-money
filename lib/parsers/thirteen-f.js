// SEC 13F informationTable XML -> normalized holdings.
// Zero runtime deps: regex on the flat per-holding block.

function pickTag(block, tag) {
  const re = new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`);
  const m = block.match(re);
  return m ? m[1].trim() : '';
}

function pickInt(s) {
  return Number(String(s).replace(/,/g, '')) || 0;
}

export function parseThirteenF(xml) {
  const holdings = [];
  const blockRe = /<infoTable>([\s\S]*?)<\/infoTable>/g;
  let m;
  while ((m = blockRe.exec(xml)) !== null) {
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
