import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import nock from 'nock';

describe('verify-edgar.js (mocked)', () => {
  beforeEach(() => {
    process.env.SEC_EDGAR_USER_AGENT = 'TestApp test@example.com';
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('fails with helpful message if env var missing', async () => {
    delete process.env.SEC_EDGAR_USER_AGENT;
    const { execSync } = await import('node:child_process');
    expect(() => execSync('node scripts/verify-edgar.js', { stdio: 'pipe' })).toThrow(/SEC_EDGAR_USER_AGENT/);
  });

  it('reports VERIFICATION PASSED when all CIKs resolve', async () => {
    // CIKs must match config/default-sources.json
    for (const cik of ['0001067983', '0001336528', '0001649339', '0001061768', '0000949509', '0001697748', '0001167483', '0001135730']) {
      nock('https://data.sec.gov')
        .get(`/submissions/CIK${cik}.json`)
        .reply(200, { cik, name: `Mock Filer ${cik}` });
    }
    nock('https://efts.sec.gov')
      .get(/LATEST\/search-index.*/)
      .reply(200, { hits: { total: { value: 5 } } });
    const { runVerify } = await import('../../scripts/verify-edgar.js');
    const logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const result = await runVerify('TestApp test@example.com');
    logSpy.mockRestore();
    expect(result.allOk).toBe(true);
    expect(result.results.every(r => r.ok)).toBe(true);
    expect(result.search.ok).toBe(true);
    expect(result.search.count).toBe(5);
  });
});