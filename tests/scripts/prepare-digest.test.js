import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, symlinkSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoCwd = join(__dirname, '..', '..');

// Minimal deterministic feed for time-seam regression tests
// (openspec/changes/add-digest-time-seam). One 13F filer with a $2B holding
// (>= $1B ⇒ normalizeValueUnits treats as dollars, no multiplication) filed
// 2026-06-25; no prior period ⇒ periodDiff returns summary: null (safe).
function writeDeterministicFeed(envDir) {
  writeFileSync(
    join(envDir, 'feed-13f.json'),
    JSON.stringify({
      schemaVersion: 1,
      thirteenF: [
        {
          filerCik: '0001067983',
          filerName: 'Test Filer',
          latestFilingDate: '2026-06-25',
          latestFormType: '13F-HR',
          latestAccessionNumber: '0001067983-26-000123',
          periodOfReport: '2026-03-31',
          history: [
            {
              filingDate: '2026-06-25',
              formType: '13F-HR',
              accessionNumber: '0001067983-26-000123',
            },
          ],
          holdings: [
            {
              cusip: '000000000',
              nameOfIssuer: 'Test',
              titleOfClass: 'COM',
              valueUsd: 2000000000,
              sshPrnamt: 100,
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

describe('prepare-digest.js', () => {
  it('emits JSON with lookbackDays applied', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 7', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    expect(j.lookbackDays).toBe(7);
    expect(j).toHaveProperty('thirteenF');
    expect(j).toHaveProperty('thirteenDG');
  });

  it('defaults to 90-day lookback (one quarter) so 13F filings appear', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    expect(j.lookbackDays).toBe(90);
  });

  it('emits diagnostics block listing valueUnitsAdjusted filers (Baupost case)', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 90', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    expect(j).toHaveProperty('diagnostics');
    expect(Array.isArray(j.diagnostics.valueUnitsAdjusted)).toBe(true);
    expect(j.diagnostics.valueUnitsAdjusted).toContain('Baupost Group');
  });

  it('attaches valueUnit and valueUnitAdjusted fields to filer entries', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 90', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    const baupost = j.thirteenF.find((f) => f.filerName === 'Baupost Group');
    const berkshire = j.thirteenF.find((f) => f.filerName === 'Berkshire Hathaway Inc');
    expect(baupost).toBeDefined();
    expect(baupost.valueUnit).toBe('thousands');
    expect(baupost.valueUnitAdjusted).toBe(true);
    expect(berkshire).toBeDefined();
    // Config-driven model: every 13F source declares `valueUnit: 'thousands'`
    // (SEC 13F <value> is in thousands). See openspec/specs/value-units-normalization.
    expect(berkshire.valueUnit).toBe('thousands');
    expect(berkshire.valueUnitAdjusted).toBe(true);
  });

  it('attaches Berkshire summary with correct exact magnitudes (no 1000× distortion)', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 90', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    const berkshire = j.thirteenF.find((f) => f.filerName === 'Berkshire Hathaway Inc');
    expect(berkshire).toBeDefined();
    expect(berkshire.summary).not.toBeNull();
    // After repair-feed-units (committed feed-13f.json normalized to thousands
    // and stamped valueUnit:'thousands'), the config-driven ×1000 produces
    // canonical dollar magnitudes. These exact values pin the regression that
    // previously produced 1000× off (trillions) figures for dollar-stored
    // snapshots — see openspec/changes/repair-feed-units.
    expect(berkshire.summary.priorTotalValueUsd).toBe(274160086701);
    expect(berkshire.summary.totalValueUsd).toBe(263095703570);
    const moved = berkshire.summary.increasedPositions + berkshire.summary.decreasedPositions;
    expect(moved).toBeGreaterThan(0);
    expect(Number.isFinite(berkshire.summary.deltaPct)).toBe(true);
    // Sanity band: a 1000× bug would push Berkshire past ~$1e13.
    expect(berkshire.summary.totalValueUsd).toBeLessThan(1e13);
  });

  it('reads from FOLLOW_THE_MONEY_FEED_DIR when set', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-prepdigest-env-'));
    try {
      // Put a tiny feed in envDir
      writeFileSync(join(envDir, 'feed-13f.json'), JSON.stringify({ thirteenF: [] }));
      mkdirSync(join(envDir, 'feed-13dg'));
      writeFileSync(
        join(envDir, 'feed-13dg', 'manifest.json'),
        JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
      );

      // Use repo cwd so node can resolve scripts/prepare-digest.js;
      // env var points feed reads to envDir (a different directory)
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        stdio: 'pipe',
      }).toString();
      const parsed = JSON.parse(out);
      expect(parsed.thirteenF).toEqual([]);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('falls back to cwd when FOLLOW_THE_MONEY_FEED_DIR is unset', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-prepdigest-fallback-'));
    try {
      writeFileSync(join(envDir, 'feed-13f.json'), JSON.stringify({ thirteenF: [] }));
      mkdirSync(join(envDir, 'feed-13dg'));
      writeFileSync(
        join(envDir, 'feed-13dg', 'manifest.json'),
        JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
      );
      // Symlink the real scripts/ dir so node can resolve `node scripts/prepare-digest.js`.
      // cwd is envDir, env var is unset → script should fall back to cwd (envDir) and read the empty feed there.
      symlinkSync(join(repoCwd, 'scripts'), join(envDir, 'scripts'));
      // The script imports from ../lib/, ../config/ etc — link those too.
      mkdirSync(join(envDir, 'lib'), { recursive: true });
      mkdirSync(join(envDir, 'config'), { recursive: true });
      const env = { ...process.env };
      delete env.FOLLOW_THE_MONEY_FEED_DIR;
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: envDir,
        env,
        stdio: 'pipe',
      }).toString();
      const parsed = JSON.parse(out);
      expect(parsed.thirteenF).toEqual([]);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('reads from envDir when set, even if envDir is empty (regression: env var not silently ignored)', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-prepdigest-missing-'));
    try {
      // envDir is empty — cwd (repoCwd) has the real feed.
      // After the fix, env var must be respected, so output should be empty feed,
      // NOT the real repo feed. Before the fix, output would contain the real feed.
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        stdio: 'pipe',
      }).toString();
      const parsed = JSON.parse(out);
      expect(parsed.thirteenF).toEqual([]);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('exposes latestFormType=13F-HR/A and history[] for amendment entries (Coatue Q4 2025)', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 90', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    // Find Coatue's Q4 2025 amendment entry (periodOfReport=2025-12-31, filed 2026-05-15)
    const coatueQ4 = j.thirteenF.find(
      (f) => f.filerName === 'Coatue Management LLC' && f.periodOfReport === '2025-12-31',
    );
    expect(coatueQ4).toBeDefined();
    expect(coatueQ4.latestFormType).toBe('13F-HR/A');
    expect(coatueQ4.latestFilingDate).toBe('2026-05-15');
    expect(Array.isArray(coatueQ4.history)).toBe(true);
    expect(coatueQ4.history.length).toBe(2);
    // history[0] must be the original 13F-HR filing (2026-02-17), history[1] the amendment
    expect(coatueQ4.history[0].formType).toBe('13F-HR');
    expect(coatueQ4.history[0].filingDate).toBe('2026-02-17');
    expect(coatueQ4.history[1].formType).toBe('13F-HR/A');
    expect(coatueQ4.history[1].filingDate).toBe('2026-05-15');
  });

  // --- Time seam regression tests (openspec/changes/add-digest-time-seam) ---

  it('produces identical output across runs for a fixed FTM_NOW and fixed feed', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-seam-det-'));
    try {
      writeDeterministicFeed(envDir);
      const env = {
        ...process.env,
        FOLLOW_THE_MONEY_FEED_DIR: envDir,
        FTM_NOW: '2026-06-26T00:00:00Z',
      };
      const out1 = execSync('node scripts/prepare-digest.js --lookback 7', {
        cwd: repoCwd,
        env,
        encoding: 'utf8',
      });
      const out2 = execSync('node scripts/prepare-digest.js --lookback 7', {
        cwd: repoCwd,
        env,
        encoding: 'utf8',
      });
      expect(out1).toBe(out2);
      const j = JSON.parse(out1);
      expect(j.generatedAt).toBe('2026-06-26T00:00:00.000Z');
      expect(j.thirteenF.length).toBe(1);
      expect(j.thirteenF[0].filerName).toBe('Test Filer');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('--now flag takes precedence over FTM_NOW env', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-seam-prec-'));
    try {
      writeDeterministicFeed(envDir);
      const env = {
        ...process.env,
        FOLLOW_THE_MONEY_FEED_DIR: envDir,
        FTM_NOW: '2026-06-26T00:00:00Z',
      };
      const out = execSync('node scripts/prepare-digest.js --lookback 7 --now 2026-03-31', {
        cwd: repoCwd,
        env,
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      // flag wins over env
      expect(j.generatedAt).toBe('2026-03-31T00:00:00.000Z');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('exits non-zero when FTM_NOW is invalid', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-seam-bad-'));
    try {
      writeDeterministicFeed(envDir);
      const env = { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir, FTM_NOW: 'not-a-date' };
      let err;
      try {
        execSync('node scripts/prepare-digest.js --lookback 7', {
          cwd: repoCwd,
          env,
          encoding: 'utf8',
          stdio: 'pipe',
        });
      } catch (e) {
        err = e;
      }
      expect(err).toBeTruthy();
      expect(err.status).not.toBe(0);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('exits non-zero when --now flag is present without a value', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-seam-noval-'));
    try {
      writeDeterministicFeed(envDir);
      const env = { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir };
      let err;
      try {
        // --now as the last arg with no following value
        execSync('node scripts/prepare-digest.js --lookback 7 --now', {
          cwd: repoCwd,
          env,
          encoding: 'utf8',
          stdio: 'pipe',
        });
      } catch (e) {
        err = e;
      }
      expect(err).toBeTruthy();
      expect(err.status).not.toBe(0);
      expect(String(err.stderr)).toContain('--now requires a value');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });
});
