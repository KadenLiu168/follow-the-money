import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, cpSync, existsSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const FIXTURE_FEED = join(REPO, 'tests', 'fixtures', 'feed-13dg');

let fakeroot;
let repoRoot;
beforeEach(() => {
  fakeroot = mkdtempSync(join(tmpdir(), 'ftm-home-'));
  repoRoot = mkdtempSync(join(tmpdir(), 'ftm-repo-'));
  if (existsSync(FIXTURE_FEED)) {
    mkdirSync(join(repoRoot, 'feed-13dg'), { recursive: true });
    cpSync(FIXTURE_FEED, join(repoRoot, 'feed-13dg'), { recursive: true });
  }
});
afterEach(() => {
  rmSync(fakeroot, { recursive: true, force: true });
  rmSync(repoRoot, { recursive: true, force: true });
});

describe('check-alerts.js', () => {
  it('emits alerts for new 13D/13D-A after lastAlertTimestamp', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }));
    const out = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, { cwd: repoRoot, encoding: 'utf8' });
    const payload = JSON.parse(out);
    expect(Array.isArray(payload.alerts)).toBe(true);
    expect(payload.alerts.length).toBeGreaterThan(0);
  });

  it('reads from FOLLOW_THE_MONEY_FEED_DIR when set', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-alerts-env-'));
    try {
      writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }));
      // envDir has an empty manifest (no filings) so output should be alerts: [].
      // cwd is repoRoot (has real fixture filings) so if env var is ignored,
      // output would contain real alerts. This is the regression check.
      mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
      writeFileSync(join(envDir, 'feed-13dg', 'manifest.json'), JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }));
      const out = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
        cwd: repoRoot,
        env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir, HOME: fakeroot },
        stdio: 'pipe',
      }).toString();
      const parsed = JSON.parse(out);
      expect(parsed.alerts).toEqual([]);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('falls back to cwd when FOLLOW_THE_MONEY_FEED_DIR is unset', async () => {
    // cwd is repoRoot which has fixture filings. With env var unset, script falls
    // back to cwd and reads the real feed → should return alerts.
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }));
    const env = { ...process.env, HOME: fakeroot };
    delete env.FOLLOW_THE_MONEY_FEED_DIR;
    const out = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, { cwd: repoRoot, env, stdio: 'pipe' }).toString();
    const parsed = JSON.parse(out);
    expect(Array.isArray(parsed.alerts)).toBe(true);
    expect(parsed.alerts.length).toBeGreaterThan(0);
  });
});