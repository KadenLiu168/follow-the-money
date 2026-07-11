import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..', '..');

// loadUserConfig reads ~/.follow-the-money/config.json via os.homedir(), which
// honors $HOME. We spawn a child with a controlled HOME and a tiny runner so
// the real module path resolution and homedir() semantics are exercised.
function loadWithHome(home) {
  const runner = join(home, 'runner.mjs');
  writeFileSync(
    runner,
    `import { loadUserConfig } from ${JSON.stringify(join(repoRoot, 'lib', 'config', 'load-user-config.js'))};\nprocess.stdout.write(JSON.stringify(loadUserConfig()));\n`,
  );
  try {
    const out = execSync(`node ${runner}`, {
      env: { ...process.env, HOME: home },
      encoding: 'utf8',
    });
    return JSON.parse(out);
  } finally {
    rmSync(runner, { force: true });
  }
}

describe('loadUserConfig', () => {
  it('falls back to { language: "en" } when config file is missing', () => {
    const home = mkdtempSync(join(tmpdir(), 'ftm-luc-missing-'));
    try {
      expect(loadWithHome(home).language).toBe('en');
    } finally {
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('falls back to { language: "en" } when config is corrupt JSON', () => {
    const home = mkdtempSync(join(tmpdir(), 'ftm-luc-corrupt-'));
    try {
      mkdirSync(join(home, '.follow-the-money'), { recursive: true });
      writeFileSync(join(home, '.follow-the-money', 'config.json'), '{ not valid json');
      expect(loadWithHome(home).language).toBe('en');
    } finally {
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('falls back to language "en" when config has no language field', () => {
    const home = mkdtempSync(join(tmpdir(), 'ftm-luc-nolang-'));
    try {
      mkdirSync(join(home, '.follow-the-money'), { recursive: true });
      writeFileSync(
        join(home, '.follow-the-money', 'config.json'),
        JSON.stringify({ frequency: 'weekly' }),
      );
      expect(loadWithHome(home).language).toBe('en');
    } finally {
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('returns the user language when present', () => {
    const home = mkdtempSync(join(tmpdir(), 'ftm-luc-zh-'));
    try {
      mkdirSync(join(home, '.follow-the-money'), { recursive: true });
      writeFileSync(
        join(home, '.follow-the-money', 'config.json'),
        JSON.stringify({ language: 'zh' }),
      );
      expect(loadWithHome(home).language).toBe('zh');
    } finally {
      rmSync(home, { recursive: true, force: true });
    }
  });

  it('does not throw on any failure path', () => {
    const home = mkdtempSync(join(tmpdir(), 'ftm-luc-throw-'));
    try {
      expect(() => loadWithHome(home)).not.toThrow();
    } finally {
      rmSync(home, { recursive: true, force: true });
    }
  });
});
