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

  it('builds archive URL from accession (strips dashes)', async () => {
    const xml = '<?xml version="1.0"?><informationTable/>';
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/form13fData.xml')
      .reply(200, xml);
    const out = await fetchThirteenFXml(client, '0001067983', '0001067983-26-000123', 'form13fData.xml');
    expect(out).toBe(xml);
  });
});