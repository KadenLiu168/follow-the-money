import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoCwd = join(__dirname, '..', '..');

// Deterministic feed with a unique filer name so we can prove which directory
// prepare-digest.js actually read. Pinned FTM_NOW keeps the test time-independent.
function writeMarkedFeed(envDir) {
  writeFileSync(
    join(envDir, 'feed-13f.json'),
    JSON.stringify({
      schemaVersion: 1,
      thirteenF: [
        {
          filerCik: '0000000000',
          filerName: 'PropMark',
          latestFilingDate: '2026-06-25',
          latestFormType: '13F-HR',
          latestAccessionNumber: '0000000000-26-000001',
          periodOfReport: '2026-03-31',
          history: [
            {
              filingDate: '2026-06-25',
              formType: '13F-HR',
              accessionNumber: '0000000000-26-000001',
            },
          ],
          holdings: [
            {
              cusip: '000000000',
              nameOfIssuer: 'Marker',
              titleOfClass: 'COM',
              valueUsd: 1000000,
              sshPrnamt: 10,
              sshPrnamtType: 'SH',
              putCall: '',
            },
          ],
          summary: null,
        },
      ],
      stats: { thirteenFFilings: 1, thirteenFHoldings: 1 },
    }),
  );
  mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
  writeFileSync(
    join(envDir, 'feed-13dg', 'manifest.json'),
    JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
  );
}

describe('feed-dir propagation (D1)', () => {
  it('fetch-feed.js --print-dir returns FOLLOW_THE_MONEY_FEED_DIR override (single source of truth)', () => {
    const custom = mkdtempSync(join(tmpdir(), 'ftm-propd-'));
    try {
      const printed = execSync('node scripts/fetch-feed.js --print-dir', {
        cwd: repoCwd,
        env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: custom },
        encoding: 'utf8',
      }).trim();
      expect(printed).toBe(custom);
    } finally {
      rmSync(custom, { recursive: true, force: true });
    }
  });

  it('prepare reads from the dir fetch resolved (no cwd divergence)', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-propd-env-'));
    try {
      writeMarkedFeed(envDir);
      const out = execSync('node scripts/prepare-digest.js --lookback 7', {
        cwd: repoCwd,
        env: {
          ...process.env,
          FOLLOW_THE_MONEY_FEED_DIR: envDir,
          FTM_NOW: '2026-06-26T00:00:00Z',
        },
        encoding: 'utf8',
      });
      const parsed = JSON.parse(out);
      const marker = parsed.thirteenF.find((f) => f.filerName === 'PropMark');
      // Marker only exists in envDir → its presence proves prepare read envDir,
      // not the repo cwd (which is the pre-fix bug).
      expect(marker).toBeDefined();
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('unset env lets prepare fall back to cwd (local mode preserved)', () => {
    const env = { ...process.env };
    delete env.FOLLOW_THE_MONEY_FEED_DIR;
    const out = execSync('node scripts/prepare-digest.js --lookback 90', {
      cwd: repoCwd,
      env: { ...env, FTM_NOW: '2026-06-26T00:00:00Z' },
      encoding: 'utf8',
    });
    const parsed = JSON.parse(out);
    // Repo cwd carries the real committed feed → real filers present (control).
    expect(parsed.thirteenF.length).toBeGreaterThan(0);
  });
});
