import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { fetchThirteenFXml } from '../../lib/edgar/fetch-thirteen-f-xml.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

describe('fetchThirteenFXml', () => {
  let client;
  beforeEach(() => {
    client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('resolves infoTable via index.json when primaryDocument is the cover page', async () => {
    // Real-world: primaryDocument is `xslForm13F_X02/primary_doc.xml` (cover page),
    // actual infoTable lives in a sibling file discovered via index.json.
    const infoTableXml = '<?xml version="1.0"?><informationTable><infoTable><cusip>037833100</cusip></infoTable></informationTable>';
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000119312526226661/index.json')
      .reply(200, {
        directory: {
          item: [
            { name: 'primary_doc.xml', size: 5555 },
            { name: '53405.xml', size: 45259 },
          ],
        },
      });
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000119312526226661/53405.xml')
      .reply(200, infoTableXml);
    const out = await fetchThirteenFXml(
      client, '0001067983', '0001193125-26-226661', 'xslForm13F_X02/primary_doc.xml'
    );
    expect(out).toBe(infoTableXml);
  });

  it('returns primaryDocument directly when index.json is unavailable (older filings)', async () => {
    // Fallback: if index.json 404s, try primaryDocument as before.
    const xml = '<?xml version="1.0"?><informationTable/>';
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/index.json')
      .reply(404);
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/form13fData.xml')
      .reply(200, xml);
    const out = await fetchThirteenFXml(client, '0001067983', '0001067983-26-000123', 'form13fData.xml');
    expect(out).toBe(xml);
  });
});