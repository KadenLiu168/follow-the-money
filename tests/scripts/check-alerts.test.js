import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execSync } from 'node:child_process';
import {
  mkdtempSync,
  writeFileSync,
  rmSync,
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
} from 'node:fs';
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
    writeFileSync(
      join(fakeroot, 'config.json'),
      JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }),
    );
    const out = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: repoRoot,
      encoding: 'utf8',
    });
    const payload = JSON.parse(out);
    expect(Array.isArray(payload.alerts)).toBe(true);
    expect(payload.alerts.length).toBeGreaterThan(0);
  });

  it('surfaces feedDir at top level equal to FOLLOW_THE_MONEY_FEED_DIR (feed-dir-transparency)', () => {
    writeFileSync(
      join(fakeroot, 'config.json'),
      JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }),
    );
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-alerts-feeddir-'));
    mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
    writeFileSync(
      join(envDir, 'feed-13dg', 'manifest.json'),
      JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
    );
    const out = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: repoRoot,
      env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir, HOME: fakeroot },
      encoding: 'utf8',
    });
    const payload = JSON.parse(out);
    expect(payload.feedDir).toBe(envDir);
  });

  it('reads from FOLLOW_THE_MONEY_FEED_DIR when set', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-alerts-env-'));
    try {
      writeFileSync(
        join(fakeroot, 'config.json'),
        JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }),
      );
      // envDir has an empty manifest (no filings) so output should be alerts: [].
      // cwd is repoRoot (has real fixture filings) so if env var is ignored,
      // output would contain real alerts. This is the regression check.
      mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
      writeFileSync(
        join(envDir, 'feed-13dg', 'manifest.json'),
        JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
      );
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
    writeFileSync(
      join(fakeroot, 'config.json'),
      JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }),
    );
    const env = { ...process.env, HOME: fakeroot };
    delete env.FOLLOW_THE_MONEY_FEED_DIR;
    const out = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: repoRoot,
      env,
      stdio: 'pipe',
    }).toString();
    const parsed = JSON.parse(out);
    expect(Array.isArray(parsed.alerts)).toBe(true);
    expect(parsed.alerts.length).toBeGreaterThan(0);
  });

  it('persists lastAlertTimestamp across runs and emits nothing on the second run', () => {
    // check-alerts.js reads ~/config.json nested under .follow-the-money/
    // (os.homedir() honors $HOME), so write the fixture config there.
    const cfgPath = join(fakeroot, '.follow-the-money', 'config.json');
    mkdirSync(join(fakeroot, '.follow-the-money'), { recursive: true });
    writeFileSync(cfgPath, JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }));
    const run1 = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: repoRoot,
      encoding: 'utf8',
    });
    const p1 = JSON.parse(run1);
    expect(p1.alerts.length).toBeGreaterThan(0);
    const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
    expect(cfg.lastAlertTimestamp).toBe('2026-06-20'); // newest alert filing in fixture
    const run2 = execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: repoRoot,
      encoding: 'utf8',
    });
    const p2 = JSON.parse(run2);
    expect(p2.alerts).toEqual([]);
  });

  it('persists the NEWEST filing date, not the oldest (no re-emit of between-run filings)', () => {
    const cfgPath = join(fakeroot, '.follow-the-money', 'config.json');
    mkdirSync(join(fakeroot, '.follow-the-money'), { recursive: true });
    writeFileSync(cfgPath, JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }));
    execSync(`HOME=${fakeroot} node ${join(REPO, 'scripts', 'check-alerts.js')}`, {
      cwd: repoRoot,
      encoding: 'utf8',
    });
    const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
    // Fixture's alert filings range 2026-01 .. 2026-06-20; persisted cursor must
    // be the newest (2026-06-20), never an older one (e.g. the oldest 2026-01-xx).
    expect(cfg.lastAlertTimestamp).toBe('2026-06-20');
    expect(cfg.lastAlertTimestamp.startsWith('2026-01-')).toBe(false);
  });
});
