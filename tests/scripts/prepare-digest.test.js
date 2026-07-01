import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { mkdirSync, writeFileSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));

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
});
