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

  it('loads .env without crashing (regression for broken dotenv import)', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ delivery: { method: 'stdout' } }));
    writeFileSync(join(fakeroot, '.env'), 'TELEGRAM_BOT_TOKEN=abc123\n');
    let out, err, status;
    try {
      out = execSync(`HOME=${fakeroot} node scripts/deliver.js --text "x"`, { encoding: 'utf8', stdio: 'pipe' });
      status = 0;
    } catch (e) {
      out = e.stdout?.toString() ?? '';
      err = e.stderr?.toString() ?? '';
      status = e.status;
    }
    expect(status).toBe(0);
    expect(err ?? '').not.toMatch(/TypeError/);
    expect(out).toMatch(/x/);
  });

  it('reaches env check when .env is present and method=telegram (proves import works)', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ delivery: { method: 'telegram' } }));
    writeFileSync(join(fakeroot, '.env'), 'TELEGRAM_BOT_TOKEN=abc123\n');
    let status = null, combined = '';
    try {
      execSync(`HOME=${fakeroot} node scripts/deliver.js --text "x"`, { stdio: 'pipe' });
      status = 0;
    } catch (e) {
      status = e.status;
      combined = `${e.stdout?.toString() ?? ''}${e.stderr?.toString() ?? ''}`;
    }
    expect(status).not.toBe(0);
    expect(combined).toMatch(/TELEGRAM_BOT_TOKEN/);
    expect(combined).not.toMatch(/TypeError/);
  });
});