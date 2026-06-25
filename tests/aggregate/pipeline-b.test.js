import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPipelineB } from '../../lib/aggregate/pipeline-b.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

let dir, httpClient, config;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-'));
  httpClient = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
  config = { thirteenDG: { enabled: true, lookbackDays: 3 } };
  nock.disableNetConnect();
});
afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); rmSync(dir, { recursive: true, force: true }); });

describe('runPipelineB', () => {
  it('appends new 13D and dedups via state', async () => {
    nock('https://efts.sec.gov')
      .get(/LATEST\/search-index.*forms=SC\+13D.*/)
      .reply(200, { hits: { hits: [{
        _source: { ciks: ['0000932470', '0001717393'], display_names: ['ICAHN CARL C', 'Jet.AI Inc'], file_date: '2026-06-20', form: 'SC 13D', adsh: '0000932470-26-000045', tickers: ['JTAI'] }
      }] } });
    nock('https://efts.sec.gov').get(/forms=SC\+13D%2FA.*/).reply(200, { hits: { hits: [] } });
    nock('https://efts.sec.gov').get(/forms=SC\+13G.*/).reply(200, { hits: { hits: [] } });
    nock('https://efts.sec.gov').get(/forms=SC\+13G%2FA.*/).reply(200, { hits: { hits: [] } });
    nock('https://www.sec.gov')
      .get(/Archives\/edgar\/data\/932470\/000093247026000045\/primary_doc\.html/)
      .reply(200, readFileSync(join(import.meta.dirname, '../fixtures/13d-primary-doc.html'), 'utf8'));
    const r = await runPipelineB({ httpClient, config, feedDir: join(dir, 'feed-13dg'), statePath: join(dir, 'state-13dg.ndjson'), lookbackDays: 3 });
    expect(r.added).toBe(1);
    expect(r.errors).toEqual([]);
  });

  it('skips already-seen accession', async () => {
    const { appendStateNdjson } = await import('../../lib/store/state-ndjson.js');
    appendStateNdjson(join(dir, 'state-13dg.ndjson'), [{ accession: '0000932470-26-000045', seenAt: 1 }]);
    nock('https://efts.sec.gov')
      .get(/.*/).reply(200, { hits: { hits: [{ _source: { ciks: ['0000932470', '0001717393'], display_names: ['ICAHN CARL C', 'Jet.AI Inc'], file_date: '2026-06-20', form: 'SC 13D', adsh: '0000932470-26-000045', tickers: ['JTAI'] } }] } });
    const r = await runPipelineB({ httpClient, config, feedDir: join(dir, 'feed-13dg'), statePath: join(dir, 'state-13dg.ndjson'), lookbackDays: 3 });
    expect(r.added).toBe(0);
  });
});
