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

// Recursively check that no object in the tree has a `hash` key (the prompt
// contract change removed hash from the output entirely).
function hasHashField(obj) {
  if (Array.isArray(obj)) return obj.some(hasHashField);
  if (obj && typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj)) {
      if (k === 'hash') return true;
      if (hasHashField(v)) return true;
    }
  }
  return false;
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

  it('surfaces feedDir at top level equal to cwd when env unset (feed-dir-transparency)', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 7', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    expect(j.feedDir).toBe(cwd);
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

  it('fails hard when FOLLOW_THE_MONEY_FEED_DIR points to an empty dir (env var respected, no silent cwd fallback)', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-prepdigest-missing-'));
    try {
      // envDir is empty — cwd (repoCwd) has the real feed. Under P3 the env var
      // MUST be respected: a missing source is a hard failure (exit 1, empty
      // stdout), NOT a silent fall-back to the real repo feed. This preserves
      // the original regression intent "env var not silently ignored".
      let err;
      try {
        execSync('node scripts/prepare-digest.js', {
          cwd: repoCwd,
          env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir },
          stdio: 'pipe',
        });
      } catch (e) {
        err = e;
      }
      expect(err).toBeTruthy();
      expect(err.status).not.toBe(0);
      expect(String(err.stderr)).toContain('missing');
      // No digest emitted on failure.
      expect(String(err.stdout ?? '')).toBe('');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  // --- D3 hard-failure (openspec/changes/no-silent-empty-digest, P3) ---

  it('fails hard when feed-13f.json is missing', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-d3-nof13-'));
    try {
      mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
      writeFileSync(
        join(envDir, 'feed-13dg', 'manifest.json'),
        JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
      );
      let err;
      try {
        execSync('node scripts/prepare-digest.js', {
          cwd: repoCwd,
          env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir },
          stdio: 'pipe',
        });
      } catch (e) {
        err = e;
      }
      expect(err).toBeTruthy();
      expect(err.status).not.toBe(0);
      expect(String(err.stderr)).toContain('feed-13f.json missing');
      expect(String(err.stdout ?? '')).toBe('');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('fails hard when feed-13dg/ is missing', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-d3-nodg-'));
    try {
      writeFileSync(join(envDir, 'feed-13f.json'), JSON.stringify({ thirteenF: [] }));
      let err;
      try {
        execSync('node scripts/prepare-digest.js', {
          cwd: repoCwd,
          env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir },
          stdio: 'pipe',
        });
      } catch (e) {
        err = e;
      }
      expect(err).toBeTruthy();
      expect(err.status).not.toBe(0);
      expect(String(err.stderr)).toContain('feed-13dg/ missing');
      expect(String(err.stdout ?? '')).toBe('');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
    }
  });

  it('fails hard when feed-13f.json is corrupt', async () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-d3-corrupt-'));
    try {
      writeFileSync(join(envDir, 'feed-13f.json'), '{ not valid json');
      mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
      writeFileSync(
        join(envDir, 'feed-13dg', 'manifest.json'),
        JSON.stringify({ schemaVersion: 1, currentYear: 2026, years: {} }),
      );
      let err;
      try {
        execSync('node scripts/prepare-digest.js', {
          cwd: repoCwd,
          env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: envDir },
          stdio: 'pipe',
        });
      } catch (e) {
        err = e;
      }
      expect(err).toBeTruthy();
      expect(err.status).not.toBe(0);
      expect(String(err.stderr)).toContain('corrupt');
      expect(String(err.stdout ?? '')).toBe('');
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

  // --- digest-output self-describing (openspec/changes/digest-output-self-describing) ---

  function writeFeedDir(envDir, { manifest, ndjson } = {}) {
    writeFileSync(join(envDir, 'feed-13f.json'), JSON.stringify({ thirteenF: [] }));
    mkdirSync(join(envDir, 'feed-13dg'), { recursive: true });
    if (manifest) {
      writeFileSync(join(envDir, 'feed-13dg', 'manifest.json'), JSON.stringify(manifest));
    }
    if (ndjson) {
      for (const [year, lines] of Object.entries(ndjson)) {
        writeFileSync(join(envDir, 'feed-13dg', `${year}.ndjson`), lines.join('\n') + '\n');
      }
    }
  }

  it('surfaces manifest count mismatch in warnings[] (regression: D2-B)', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-warn-mismatch-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-warn-home-'));
    try {
      writeFeedDir(envDir, {
        manifest: {
          schemaVersion: 1,
          currentYear: 2026,
          years: { 2026: { file: 'feed-13dg/2026.ndjson', count: 5 } },
        },
        ndjson: {
          2026: [
            '{"filingDate":"2026-01-01"}',
            '{"filingDate":"2026-02-01"}',
            '{"filingDate":"2026-03-01"}',
          ],
        },
      });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      expect(Array.isArray(j.warnings)).toBe(true);
      expect(j.warnings.length).toBeGreaterThan(0);
      expect(j.warnings.some((w) => /manifest says 5, file has 3/.test(w))).toBe(true);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('surfaces missing year file in warnings[]', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-warn-missing-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-warn-home2-'));
    try {
      writeFeedDir(envDir, {
        manifest: {
          schemaVersion: 1,
          currentYear: 2026,
          years: { 2025: { file: 'feed-13dg/2025.ndjson', count: 1 } },
        },
        // 2025.ndjson intentionally not written
      });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      expect(j.warnings.some((w) => /2025: file missing/.test(w))).toBe(true);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('produces empty warnings on a clean run', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-warn-clean-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-warn-home3-'));
    try {
      writeFeedDir(envDir, { manifest: { schemaVersion: 1, currentYear: 2026, years: {} } });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      expect(j.warnings).toEqual([]);
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('renderContext.language falls back to "en" when user config missing', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-rc-lang-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-rc-home-'));
    try {
      writeFeedDir(envDir, { manifest: { schemaVersion: 1, currentYear: 2026, years: {} } });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      expect(j.renderContext.language).toBe('en');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('renderContext.language reflects user config when present', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-rc-lang2-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-rc-home2-'));
    try {
      mkdirSync(join(home, '.follow-the-money'), { recursive: true });
      writeFileSync(
        join(home, '.follow-the-money', 'config.json'),
        JSON.stringify({ language: 'zh' }),
      );
      writeFeedDir(envDir, { manifest: { schemaVersion: 1, currentYear: 2026, years: {} } });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      expect(j.renderContext.language).toBe('zh');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('renderContext.prompts reports user override and embeds the user file text', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-rc-user-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-rc-home3-'));
    try {
      mkdirSync(join(home, '.follow-the-money', 'prompts'), { recursive: true });
      writeFileSync(join(home, '.follow-the-money', 'prompts', 'format-13f.md'), '# user override');
      writeFeedDir(envDir, { manifest: { schemaVersion: 1, currentYear: 2026, years: {} } });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      expect(j.renderContext.prompts.format_13f.source).toBe('user');
      expect(j.renderContext.prompts.format_13f.text).toBe('# user override');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('renderContext.prompts embeds non-empty text and exposes no hash/config state', () => {
    const envDir = mkdtempSync(join(tmpdir(), 'ftm-rc-repo-'));
    const home = mkdtempSync(join(tmpdir(), 'ftm-rc-home4-'));
    try {
      writeFeedDir(envDir, { manifest: { schemaVersion: 1, currentYear: 2026, years: {} } });
      const out = execSync('node scripts/prepare-digest.js', {
        cwd: repoCwd,
        env: { ...process.env, HOME: home, FOLLOW_THE_MONEY_FEED_DIR: envDir },
        encoding: 'utf8',
      });
      const j = JSON.parse(out);
      // No user override here, so the tier is network-dependent (repo or
      // remote). Both are valid; we only assert the embedded text is real.
      const src = j.renderContext.prompts.format_13f.source;
      expect(['repo', 'remote']).toContain(src);
      const text = j.renderContext.prompts.format_13f.text;
      expect(typeof text).toBe('string');
      expect(text.length).toBeGreaterThan(0);
      // Requirement: output SHALL NOT embed a prompt hash or config state.
      expect(hasHashField(j)).toBe(false);
      expect(j.renderContext).toEqual({ language: 'en', prompts: j.renderContext.prompts });
      expect(j.renderContext).not.toHaveProperty('lastAlertTimestamp');
      expect(j.renderContext).not.toHaveProperty('frequency');
    } finally {
      rmSync(envDir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
    }
  });
});
