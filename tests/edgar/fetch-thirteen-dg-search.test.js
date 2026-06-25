import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { fetchThirteenDGSearch } from '../../lib/edgar/fetch-thirteen-dg-search.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(__dirname, '../fixtures/search-13dg.json'), 'utf8'));

describe('fetchThirteenDGSearch', () => {
  let client;
  beforeEach(() => {
    client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('queries EDGAR full-text search with the form and date range', async () => {
    const scope = nock('https://efts.sec.gov')
      .get(/LATEST\/search-index.*forms=SC\+13D.*startDate=2026-06-20.*endDate=2026-06-25/)
      .reply(200, fixture);
    const r = await fetchThirteenDGSearch(client, {
      startDate: '2026-06-20', endDate: '2026-06-25', formType: 'SC 13D',
    });
    expect(r).toHaveLength(2);
    expect(r[0]._source.form).toBe('SC 13D');
    expect(scope.isDone()).toBe(true);
  });

  it('encodes form name with + (not %20) per EDGAR convention', async () => {
    let capturedUrl = null;
    nock('https://efts.sec.gov').get(/.*/).reply(200, (uri) => { capturedUrl = uri; return fixture; });
    await fetchThirteenDGSearch(client, { startDate: '2026-06-20', endDate: '2026-06-25', formType: 'SC 13G/A' });
    expect(capturedUrl).toMatch(/forms=SC\+13G%2FA/);
  });
});