import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let fakeroot;
beforeEach(() => { fakeroot = mkdtempSync(join(tmpdir(), 'ftm-home-')); });
afterEach(() => { rmSync(fakeroot, { recursive: true, force: true }); });

describe('deliver.js', () => {
  it('writes to stdout for default config', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ delivery: { method: 'stdout' } }));
    const out = execSync(`HOME=${fakeroot} node scripts/deliver.js --text "hello"`, { encoding: 'utf8' });
    expect(out).toMatch(/hello/);
  });

  it('exits non-zero if method=telegram but env var missing', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ delivery: { method: 'telegram' } }));
    expect(() => execSync(`HOME=${fakeroot} node scripts/deliver.js --text "x"`, { stdio: 'pipe' })).toThrow(/TELEGRAM_BOT_TOKEN/);
  });
});