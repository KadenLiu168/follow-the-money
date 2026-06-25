import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { fetchLatest13FFilings } from '../../lib/edgar/fetch-submissions.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('fetchLatest13FFilings', () => {
  let client;
  beforeEach(() => {
    client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('returns only 13F-HR and 13F-HR/A, sorted desc', async () => {
    const fixture = JSON.parse(readFileSync(join(__dirname, '../fixtures/submissions-cik-0001067983.json'), 'utf8'));
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, fixture);
    const r = await fetchLatest13FFilings(client, '0001067983');
    expect(r).toHaveLength(2);
    expect(r[0].formType).toBe('13F-HR/A'); // most recent
    expect(r[1].formType).toBe('13F-HR');
  });

  it('handles 10-digit CIK with and without leading zeros', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-01-01'], accessionNumber: ['0001067983-26-000001'], primaryDocument: ['form13fData.xml'], reportDate: ['2025-12-31'] } },
    });
    const r = await fetchLatest13FFilings(client, '1067983');
    expect(r).toHaveLength(1);
    expect(r[0].accessionNumber).toBe('0001067983-26-000001');
  });
});