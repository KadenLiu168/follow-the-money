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
    // 13F holdings live in form13fInfoTable.xml, discovered via index.json —
    // the cover page (form13fData.xml) is NOT a holdings source.
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/index.json')
      .reply(200, { directory: { item: [
        { name: 'form13fInfoTable.xml', size: 5000 },
        { name: 'primary_doc.xml', size: 3000 },
      ] } });
    nock('https://www.sec.gov').get('/Archives/edgar/data/1067983/000106798326000123/form13fInfoTable.xml').reply(200, readFileSync(join(import.meta.dirname, '../fixtures/form13fData.xml'), 'utf8'));
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
    // CIK 0001067983 resolves the infoTable via index.json (must succeed).
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/index.json')
      .reply(200, { directory: { item: [ { name: 'form13fInfoTable.xml', size: 5000 } ] } });
    nock('https://www.sec.gov').get(/.*form13fInfoTable.xml.*/).reply(200, readFileSync(join(import.meta.dirname, '../fixtures/form13fData.xml'), 'utf8'));
    const r = await runPipelineA({ httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json') });
    expect(r.errors).toHaveLength(1);
    expect(r.errors[0].cik).toBe('0000000001');
  });

  it('compares against prior period holdings of the same filer (regardless of CIK padding)', async () => {
    // First filing (Q4 2025)
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: {
        form: ['13F-HR', '13F-HR'],
        filingDate: ['2025-11-14', '2026-05-15'],
        accessionNumber: ['0001067983-25-999001', '0001067983-26-000123'],
        primaryDocument: ['form13fData.xml', 'form13fData.xml'],
        reportDate: ['2025-09-30', '2026-03-31'],
      } },
    });
    // First filing has AAPL, second has AAPL+GOOG
    const xmlQ4 = '<?xml version="1.0"?><informationTable><infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>1000</value><shrsOrPrnAmt><sshPrnamt>100</sshPrnamt></shrsOrPrnAmt><votingAuthority><Sole>100</Sole><Shared>0</Shared><None>0</None></votingAuthority></infoTable></informationTable>';
    const xmlQ1 = '<?xml version="1.0"?><informationTable><infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>2000</value><shrsOrPrnAmt><sshPrnamt>200</sshPrnamt></shrsOrPrnAmt><votingAuthority><Sole>200</Sole><Shared>0</Shared><None>0</None></votingAuthority></infoTable><infoTable><nameOfIssuer>ALPHABET INC</nameOfIssuer><cusip>02079K305</cusip><value>3000</value><shrsOrPrnAmt><sshPrnamt>50</sshPrnamt></shrsOrPrnAmt><votingAuthority><Sole>50</Sole><Shared>0</Shared><None>0</None></votingAuthority></infoTable></informationTable>';
    // Both filings resolve the infoTable via index.json (not the cover page).
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798325999001/index.json')
      .reply(200, { directory: { item: [ { name: 'form13fInfoTable.xml', size: 5000 } ] } });
    nock('https://www.sec.gov').get('/Archives/edgar/data/1067983/000106798325999001/form13fInfoTable.xml').reply(200, xmlQ4);
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/index.json')
      .reply(200, { directory: { item: [ { name: 'form13fInfoTable.xml', size: 5000 } ] } });
    nock('https://www.sec.gov').get('/Archives/edgar/data/1067983/000106798326000123/form13fInfoTable.xml').reply(200, xmlQ1);
    const r = await runPipelineA({
      httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json'),
    });
    expect(r.added).toBe(2);
    // Q1 entry should show: 1 new (GOOG), 0 closed, 1 increased (AAPL 100→200)
    const q1 = JSON.parse(readFileSync(join(dir, 'feed-13f.json'), 'utf8'))
      .thirteenF.find(e => e.periodOfReport === '2026-03-31');
    expect(q1.summary.newPositions).toContain('02079K305');        // GOOG is new
    expect(q1.summary.closedPositions).toEqual([]);                // nothing closed
    expect(q1.summary.increasedPositions).toBe(1);                 // AAPL increased
  });
});