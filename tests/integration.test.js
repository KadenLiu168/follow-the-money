// tests/integration.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync, readFileSync, existsSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..');

let workdir, homedir, stubDir;
beforeEach(() => {
  workdir = mkdtempSync(join(tmpdir(), 'ftm-int-'));
  homedir = mkdtempSync(join(tmpdir(), 'ftm-home-'));
  writeFileSync(
    join(homedir, 'config.json'),
    JSON.stringify({ lastAlertTimestamp: '1970-01-01T00:00:00.000Z' }),
  );
  nock.disableNetConnect();
});
afterEach(() => {
  nock.cleanAll();
  nock.enableNetConnect();
  rmSync(workdir, { recursive: true, force: true });
  rmSync(homedir, { recursive: true, force: true });
  rmSync(stubDir, { recursive: true, force: true });
});

describe('integration: aggregate → digest → alert', () => {
  it('produces a digest and an alert from stubbed EDGAR', async () => {
    const fixtures = {
      submissions: {
        filings: {
          recent: {
            form: ['13F-HR'],
            filingDate: ['2026-06-25'],
            accessionNumber: ['0001067983-26-000123'],
            primaryDocument: ['form13fData.xml'],
            reportDate: ['2026-03-31'],
          },
        },
      },
      form13fXml: readFileSync(join(__dirname, 'fixtures/form13fData.xml'), 'utf8'),
      search13dg: {
        hits: {
          hits: [
            {
              _source: {
                ciks: ['0000932470', '0001717393'],
                display_names: ['ICAHN CARL C', 'Jet.AI Inc'],
                file_date: '2026-06-29',
                form: 'SC 13D',
                adsh: '0000932470-26-000045',
                tickers: ['JTAI'],
              },
            },
          ],
        },
      },
      primaryDoc: readFileSync(join(__dirname, 'fixtures/13d-primary-doc.html'), 'utf8'),
    };

    // Write a child-process loader that installs fetch stubs from env JSON
    stubDir = mkdtempSync(join(tmpdir(), 'ftm-stub-'));
    const stubPath = join(stubDir, 'stub-fetch.mjs');
    writeFileSync(
      stubPath,
      `
const fixtures = JSON.parse(process.env.FIXTURES_JSON);
const orig = globalThis.fetch;
globalThis.fetch = async (url, opts = {}) => {
  const u = String(url);
  // 13F submissions
  let m = u.match(/^https:\\/\\/data\\.sec\\.gov\\/submissions\\/CIK(\\d+)\\.json$/);
  if (m) {
    return new Response(JSON.stringify(fixtures.submissions), { status: 200 });
  }
  // 13F index.json — holdings live in form13fInfoTable.xml (not the cover page)
  m = u.match(/^https:\\/\\/www\\.sec\\.gov\\/Archives\\/edgar\\/data\\/1067983\\/000106798326000123\\/index\\.json$/);
  if (m) {
    return new Response(JSON.stringify({ directory: { item: [
      { name: 'form13fInfoTable.xml', size: 5000 },
      { name: 'primary_doc.xml', size: 3000 },
    ] } }), { status: 200, headers: { 'content-type': 'application/json' } });
  }
  // 13F XML (information table)
  m = u.match(/^https:\\/\\/www\\.sec\\.gov\\/Archives\\/edgar\\/data\\/1067983\\/000106798326000123\\/form13fInfoTable\\.xml$/);
  if (m) {
    return new Response(fixtures.form13fXml, { status: 200, headers: { 'content-type': 'text/xml' } });
  }
  // 13D/G search
  if (/^https:\\/\\/efts\\.sec\\.gov\\/LATEST\\/search-index/.test(u)) {
    return new Response(JSON.stringify(fixtures.search13dg), { status: 200 });
  }
  // 13D/G primary doc
  m = u.match(/^https:\\/\\/www\\.sec\\.gov\\/Archives\\/edgar\\/data\\/932470\\/000093247026000045\\/primary_doc\\.html$/);
  if (m) {
    return new Response(fixtures.primaryDoc, { status: 200, headers: { 'content-type': 'text/html' } });
  }
  // Unknown: real fetch (will likely fail / rate limit); return empty 404
  return new Response('', { status: 404 });
};
`,
    );

    const env = {
      ...process.env,
      SEC_EDGAR_USER_AGENT: 'T t@e.com',
      FIXTURES_JSON: JSON.stringify(fixtures),
    };
    // Run aggregator with child-process fetch stub via --import
    execSync(`node --import=${stubPath} ${join(REPO, 'scripts', 'aggregate.js')}`, {
      cwd: workdir,
      env,
      encoding: 'utf8',
    });

    // Assert feed files were written
    expect(existsSync(join(workdir, 'feed-13f.json'))).toBe(true);
    expect(existsSync(join(workdir, 'feed-13dg', 'manifest.json'))).toBe(true);
    expect(existsSync(join(workdir, 'feed-13dg', '2026.ndjson'))).toBe(true);

    // Run digest. Pin the reference time via FTM_NOW so the fixed fixture
    // dates (2026-06-25 / 2026-06-29) always fall inside --lookback 7,
    // making this test deterministic regardless of the real wall-clock date.
    // See openspec/changes/add-digest-time-seam (capability: digest-lookback).
    const digestOut = execSync(`node ${join(REPO, 'scripts', 'prepare-digest.js')} --lookback 7`, {
      cwd: workdir,
      env: { ...process.env, FTM_NOW: '2026-06-26T00:00:00Z' },
      encoding: 'utf8',
    });
    const digest = JSON.parse(digestOut);
    expect(digest.thirteenF.length).toBeGreaterThan(0);
    expect(digest.thirteenDG.length).toBeGreaterThan(0);

    // Run alerts
    const alertOut = execSync(`HOME=${homedir} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: workdir,
      encoding: 'utf8',
    });
    const payload = JSON.parse(alertOut);
    expect(payload.alerts.length).toBeGreaterThan(0);
    expect(payload.alerts[0].filerName).toBeTruthy();
  });
});
