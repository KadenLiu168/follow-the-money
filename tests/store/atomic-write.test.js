import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { existsSync, readFileSync, mkdirSync, rmSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { atomicWriteJSON, atomicWriteText } from '../../lib/store/atomic-write.js';

const dir = join(tmpdir(), `ftm-atomic-write-${process.pid}`);
// The helper intentionally does NOT auto-create the destination directory
// (so it can throw when the dir is missing — per spec). Success-path tests
// must create `dir` themselves; the `missing/` subpath is never created, so
// the throw-path tests still exercise the "dir does not exist" case.
beforeEach(() => { mkdirSync(dir, { recursive: true }); });
afterEach(() => { try { rmSync(dir, { recursive: true, force: true }); } catch {} });

describe('atomicWriteJSON', () => {
  it('writes content identical to inline JSON.stringify(obj, null, 2)', () => {
    const path = join(dir, 'feed.json');
    const obj = { a: 1, b: [1, 2, 3], c: { d: 'x' } };
    atomicWriteJSON(path, obj);
    expect(readFileSync(path, 'utf8')).toBe(JSON.stringify(obj, null, 2));
  });

  it('is atomic: no leftover .tmp file after a successful write', () => {
    const path = join(dir, 'feed.json');
    atomicWriteJSON(path, { ok: true });
    const leftover = readdirSync(dir).filter(f => f.endsWith('.tmp'));
    expect(leftover).toHaveLength(0);
    expect(existsSync(path)).toBe(true);
  });

  it('throws (and leaves no corrupt path) when the destination directory does not exist', () => {
    const path = join(dir, 'missing', 'feed.json');
    expect(() => atomicWriteJSON(path, { x: 1 })).toThrow();
    expect(existsSync(path)).toBe(false);
  });
});

describe('atomicWriteText', () => {
  it('writes the raw string atomically and unchanged', () => {
    const path = join(dir, 'raw.txt');
    const str = 'line one\nline two\n';
    atomicWriteText(path, str);
    expect(readFileSync(path, 'utf8')).toBe(str);
  });

  it('throws when the destination directory does not exist', () => {
    const path = join(dir, 'missing', 'raw.txt');
    expect(() => atomicWriteText(path, 'x')).toThrow();
    expect(existsSync(path)).toBe(false);
  });
});
