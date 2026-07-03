import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { mkdtempSync, rmSync, existsSync, readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fetchFeed } from '../../lib/fetch/fetch-feed.js';

let dir;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-fetch-'));
  nock.disableNetConnect();
});
afterEach(() => {
  nock.cleanAll();
  nock.enableNetConnect();
  rmSync(dir, { recursive: true, force: true });
});

const OWNER = 'KadenLiu168';
const REPO = 'follow-the-money';
const BRANCH = 'main';
const RAW = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}`;

describe('fetchFeed', () => {
  it('returns ok=true and writes all 5 files when all upstream requests succeed', async () => {
    nock(RAW).get('/feed-13f.json').reply(200, '{"thirteenF":[]}');
    nock(RAW).get('/state-13f.json').reply(200, '{"seenFilings":{}}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({
      schemaVersion: 1, currentYear: 2026, years: { 2024: { file: 'feed-13dg/2024.ndjson', count: 1, firstDate: '2024-12-01', lastDate: '2024-12-31' } },
    }));
    nock(RAW).get('/feed-13dg/2024.ndjson').reply(200, '{"formType":"SC 13D"}\n');
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(result.ok).toBe(true);
    expect(result.filesWritten).toEqual(expect.arrayContaining([
      'feed-13f.json', 'state-13f.json', 'feed-13dg/manifest.json', 'feed-13dg/2024.ndjson', 'state-13dg.ndjson',
    ]));
    expect(existsSync(join(dir, 'feed-13f.json'))).toBe(true);
    expect(readFileSync(join(dir, 'feed-13f.json'), 'utf8')).toBe('{"thirteenF":[]}');
    expect(readdirSync(join(dir, 'feed-13dg'))).toEqual(['2024.ndjson', 'manifest.json']);
  });

  it('returns ok=false with reason when feed-13f.json 404s; other successes in partialFilesWritten', async () => {
    nock(RAW).get('/feed-13f.json').reply(404, 'Not Found');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({ years: {} }));
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(result.ok).toBe(false);
    expect(result.reason).toMatch(/feed-13f\.json/);
    expect(result.reason).toMatch(/404/);
    expect(result.partialFilesWritten).toEqual(expect.arrayContaining(['state-13f.json', 'feed-13dg/manifest.json', 'state-13dg.ndjson']));
    expect(result.partialFilesWritten).not.toContain('feed-13f.json');
    expect(existsSync(join(dir, 'feed-13f.json'))).toBe(false);
  });

  it('returns ok=false when manifest 404s (cannot discover NDJSON files)', async () => {
    nock(RAW).get('/feed-13f.json').reply(200, '{}');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(404, 'Not Found');
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(result.ok).toBe(false);
    expect(result.reason).toMatch(/manifest/);
    expect(result.partialFilesWritten).toEqual(expect.arrayContaining(['feed-13f.json', 'state-13f.json', 'state-13dg.ndjson']));
  });

  it('returns ok=true with warning when one NDJSON year is missing (manifest still lists it)', async () => {
    nock(RAW).get('/feed-13f.json').reply(200, '{}');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({
      years: { 2024: { file: 'feed-13dg/2024.ndjson' }, 2025: { file: 'feed-13dg/2025.ndjson' } },
    }));
    nock(RAW).get('/feed-13dg/2024.ndjson').reply(200, '');
    nock(RAW).get('/feed-13dg/2025.ndjson').reply(404, 'Not Found');
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(result.ok).toBe(true);
    expect(result.filesWritten).toContain('feed-13dg/2024.ndjson');
    expect(result.filesWritten).not.toContain('feed-13dg/2025.ndjson');
  });

  it('overwrites existing files in targetDir atomically (writes to .tmp then rename)', async () => {
    // Pre-populate with stale content
    writeFileSync(join(dir, 'feed-13f.json'), 'STALE');
    nock(RAW).get('/feed-13f.json').reply(200, 'FRESH');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({ years: {} }));
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(readFileSync(join(dir, 'feed-13f.json'), 'utf8')).toBe('FRESH');
    // No leftover .tmp file
    expect(existsSync(join(dir, 'feed-13f.json.tmp'))).toBe(false);
  });

  it('retries on transient failure then succeeds (network flakiness)', async () => {
    nock(RAW).get('/feed-13f.json').replyWithError({ message: 'ECONNRESET' });
    nock(RAW).get('/feed-13f.json').replyWithError({ message: 'ECONNRESET' });
    nock(RAW).get('/feed-13f.json').reply(200, '{"thirteenF":[]}');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({ years: {} }));
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir, retries: 2 });

    expect(result.ok).toBe(true);
  });

  it('returns ok=false after exhausting retries', async () => {
    nock(RAW).get('/feed-13f.json').times(3).replyWithError({ message: 'ECONNRESET' });
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({ years: {} }));
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir, retries: 2 });

    expect(result.ok).toBe(false);
    expect(result.reason).toMatch(/feed-13f\.json/);
  });

  it('returns ok=false when writeAtomic fails for a static file (hard fail)', async () => {
    nock(RAW).get('/feed-13f.json').reply(200, '{"thirteenF":[]}');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({ years: {} }));
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    // Force writeAtomic to fail by pre-creating a directory at the .tmp path,
    // so writeFile throws EISDIR.
    mkdirSync(join(dir, 'feed-13f.json.tmp'));

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(result.ok).toBe(false);
    expect(result.reason).toMatch(/feed-13f\.json/);
    // No throw — module returns result object as spec requires
  });

  it('returns ok=true (soft fail) when writeAtomic fails for an NDJSON file', async () => {
    nock(RAW).get('/feed-13f.json').reply(200, '{}');
    nock(RAW).get('/state-13f.json').reply(200, '{}');
    nock(RAW).get('/feed-13dg/manifest.json').reply(200, JSON.stringify({
      years: { 2024: { file: 'feed-13dg/2024.ndjson' }, 2025: { file: 'feed-13dg/2025.ndjson' } },
    }));
    nock(RAW).get('/feed-13dg/2024.ndjson').reply(200, '');
    nock(RAW).get('/feed-13dg/2025.ndjson').reply(200, '');
    nock(RAW).get('/state-13dg.ndjson').reply(200, '');

    // Force writeAtomic to fail only for the 2025 NDJSON file.
    // Create feed-13dg/ first so mkdir of the .tmp path's parent succeeds,
    // then create the .tmp path itself as a directory so writeFile throws EISDIR.
    mkdirSync(join(dir, 'feed-13dg'), { recursive: true });
    mkdirSync(join(dir, 'feed-13dg', '2025.ndjson.tmp'));

    const result = await fetchFeed({ repoOwner: OWNER, repoName: REPO, targetDir: dir });

    expect(result.ok).toBe(true);
    expect(result.filesWritten).not.toContain('feed-13dg/2025.ndjson');
    // Other files succeeded
    expect(result.filesWritten).toEqual(expect.arrayContaining([
      'feed-13f.json', 'state-13f.json', 'feed-13dg/manifest.json', 'feed-13dg/2024.ndjson', 'state-13dg.ndjson',
    ]));
  });
});