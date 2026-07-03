import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, symlinkSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoCwd = join(__dirname, '..', '..');

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
    expect(berkshire.valueUnit).toBe('dollars');
    expect(berkshire.valueUnitAdjusted).toBeUndefined();
  });

  it('attaches Berkshire summary with concrete new/closed/delta values', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 90', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    const berkshire = j.thirteenF.find((f) => f.filerName === 'Berkshire Hathaway Inc');
    expect(berkshire).toBeDefined();
    expect(berkshire.summary).not.toBeNull();
    // Berkshire has known Q4 2025 → Q1 2026 transition; prior total should be Q4 2025 ~$274B
    expect(berkshire.summary.priorTotalValueUsd).toBe(274160086701);
    expect(berkshire.summary.totalValueUsd).toBe(263095703570);
    // At least one of increased/decreased should be positive (Berkshire always trades)
    const moved = berkshire.summary.increasedPositions + berkshire.summary.decreasedPositions;
    expect(moved).toBeGreaterThan(0);
    // deltaPct should be a finite number
    expect(Number.isFinite(berkshire.summary.deltaPct)).toBe(true);
  });

  it('reads from FOLLOW_THE_MONEY_FEED_DIR when set', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-prepdigest-env-'));
    try {
      // Put a tiny feed in envDir
      writeFileSync(join(envDir, 'feed-13f.json'), JSON.stringify({ thirteenF: [] }));
      mkdirSync(join(envDir, 'feed-13dg'));
      writeFileSync(join(envDir, 'feed-13dg', 'manifest.json'), JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }));

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
      writeFileSync(join(envDir, 'feed-13dg', 'manifest.json'), JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }));
      // Symlink the real scripts/ dir so node can resolve `node scripts/prepare-digest.js`.
      // cwd is envDir, env var is unset → script should fall back to cwd (envDir) and read the empty feed there.
      symlinkSync(join(repoCwd, 'scripts'), join(envDir, 'scripts'));
      // The script imports from ../lib/, ../config/ etc — link those too.
      mkdirSync(join(envDir, 'lib'), { recursive: true });
      mkdirSync(join(envDir, 'config'), { recursive: true });
      const env = { ...process.env };
      delete env.FOLLOW_THE_MONEY_FEED_DIR;
      const out = execSync('node scripts/prepare-digest.js', { cwd: envDir, env, stdio: 'pipe' }).toString();
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
});
