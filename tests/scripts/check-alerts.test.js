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
});