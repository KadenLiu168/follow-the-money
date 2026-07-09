import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseThirteenF } from '../../lib/parsers/thirteen-f.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const xml = readFileSync(join(__dirname, '../fixtures/form13fData.xml'), 'utf8');

describe('parseThirteenF', () => {
  it('parses holdings with voting authority split', () => {
    const r = parseThirteenF(xml);
    expect(r).toHaveLength(1);
    expect(r[0]).toMatchObject({
      cusip: '037833100',
      issuerName: 'APPLE INC',
      valueUsd: 58200000000,
      shares: 300000000,
      votingAuthority: { sole: 300000000, shared: 0, none: 0 },
    });
  });

  it('throws on empty <informationTable/> instead of silently returning []', () => {
    expect(() => parseThirteenF('<?xml version="1.0"?><informationTable/>')).toThrow(/0 holdings/);
  });

  it('throws when XML has no <infoTable> at all (cover page parsed as holdings)', () => {
    expect(() => parseThirteenF('<?xml version="1.0"?><form13F><coverPage/></form13F>')).toThrow(/0 holdings/);
  });

  it('handles namespaced infoTable elements (Baupost, some filers use xmlns:ns1)', () => {
    // Some filers' XML declares xmlns:ns1="..." and uses <ns1:infoTable> instead of <infoTable>.
    const namespaced = `<?xml version="1.0" encoding="UTF-8"?>
<ns1:informationTable xmlns:ns1="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <ns1:infoTable>
    <ns1:nameOfIssuer>ALPHABET INC</ns1:nameOfIssuer>
    <ns1:cusip>02079K305</ns1:cusip>
    <ns1:value>1234567</ns1:value>
    <ns1:shrsOrPrnAmt><ns1:sshPrnamt>5000000</ns1:sshPrnamt></ns1:shrsOrPrnAmt>
    <ns1:votingAuthority><ns1:Sole>5000000</ns1:Sole><ns1:Shared>0</ns1:Shared><ns1:None>0</ns1:None></ns1:votingAuthority>
  </ns1:infoTable>
</ns1:informationTable>`;
    const r = parseThirteenF(namespaced);
    expect(r).toHaveLength(1);
    expect(r[0]).toMatchObject({
      cusip: '02079K305',
      issuerName: 'ALPHABET INC',
      shares: 5000000,
      valueUsd: 1234567,
    });
  });
});
