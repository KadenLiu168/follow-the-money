import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPipelineA } from '../../lib/aggregate/pipeline-a.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

let dir, httpClient, config;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-'));
  httpClient = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
  config = { thirteenF: [{ cik: '0001067983', name: 'Berkshire Hathaway Inc' }] };
  nock.disableNetConnect();
});
afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); rmSync(dir, { recursive: true, force: true }); });

describe('runPipelineA', () => {
  it('fetches, parses, upserts one 13F entry', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    nock('https://www.sec.gov').get('/Archives/edgar/data/1067983/000106798326000123/form13fData.xml').reply(200, readFileSync(join(import.meta.dirname, '../fixtures/form13fData.xml'), 'utf8'));
    const r = await runPipelineA({
      httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json'),
    });
    expect(r.added).toBe(1);
    expect(r.errors).toEqual([]);
  });

  it('skips already-seen accession (state dedup)', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    // Pre-seed state
    const { writeStateJson } = await import('../../lib/store/state-json.js');
    writeStateJson(join(dir, 'state-13f.json'), { lastUpdated: 'x', seenFilings: { '0001067983-26-000123': 1 } });
    const r = await runPipelineA({
      httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json'),
    });
    expect(r.added).toBe(0);
  });

  it('captures error per CIK, continues with others', async () => {
    config = { thirteenF: [
      { cik: '0001067983', name: 'A' },
      { cik: '0000000001', name: 'B' },
    ]};
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    nock('https://data.sec.gov').get('/submissions/CIK0000000001.json').reply(500);
    nock('https://www.sec.gov').get(/.*form13fData.xml.*/).reply(200, readFileSync(join(import.meta.dirname, '../fixtures/form13fData.xml'), 'utf8'));
    const r = await runPipelineA({ httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json') });
    expect(r.errors).toHaveLength(1);
    expect(r.errors[0].cik).toBe('0000000001');
  });
});