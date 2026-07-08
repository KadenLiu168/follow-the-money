import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let fakeroot;
beforeEach(() => { fakeroot = mkdtempSync(join(tmpdir(), 'ftm-print-')); });
afterEach(() => { rmSync(fakeroot, { recursive: true, force: true }); });

describe('print.js', () => {
  it('writes --text to stdout', () => {
    const out = execSync(`node scripts/print.js --text "hello"`, { encoding: 'utf8' });
    expect(out).toMatch(/hello/);
  });

  it('writes --file contents to stdout', () => {
    const digestPath = join(fakeroot, 'digest.txt');
    writeFileSync(digestPath, 'hello-from-file');
    const out = execSync(`node scripts/print.js --file ${digestPath}`, { encoding: 'utf8' });
    expect(out).toMatch(/hello-from-file/);
  });

  it('exits non-zero with stderr error when neither --text nor --file is given', () => {
    let status = null, combined = '';
    try {
      execSync(`node scripts/print.js`, { stdio: 'pipe' });
      status = 0;
    } catch (e) {
      status = e.status;
      combined = `${e.stdout?.toString() ?? ''}${e.stderr?.toString() ?? ''}`;
    }
    expect(status).not.toBe(0);
    expect(combined).toMatch(/--text or --file/);
  });

  it('exits non-zero with stderr error when --file path is missing', () => {
    let status = null, combined = '';
    try {
      execSync(`node scripts/print.js --file ${join(fakeroot, 'does-not-exist.txt')}`, { stdio: 'pipe' });
      status = 0;
    } catch (e) {
      status = e.status;
      combined = `${e.stdout?.toString() ?? ''}${e.stderr?.toString() ?? ''}`;
    }
    expect(status).not.toBe(0);
    expect(combined).toMatch(/failed to read/);
  });
});