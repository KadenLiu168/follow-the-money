import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readStateNdjson, appendStateNdjson } from '../../lib/store/state-ndjson.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('state-ndjson', () => {
  it('returns empty entries when file missing', () => {
    expect(readStateNdjson(join(dir, 'missing.ndjson')).entries).toEqual([]);
  });

  it('appends entries and round-trips', () => {
    const p = join(dir, 's.ndjson');
    appendStateNdjson(p, [{ accession: 'A', seenAt: 1 }]);
    appendStateNdjson(p, [{ accession: 'B', seenAt: 2 }]);
    expect(readStateNdjson(p).entries).toEqual([
      { accession: 'A', seenAt: 1 },
      { accession: 'B', seenAt: 2 },
    ]);
  });

  it('skips blank lines on read', () => {
    const p = join(dir, 's.ndjson');
    appendStateNdjson(p, [{ accession: 'A', seenAt: 1 }]);
    expect(readStateNdjson(p).entries.length).toBe(1);
  });

  it('counts corrupt lines as skipped', () => {
    const p = join(dir, 's.ndjson');
    writeFileSync(p, `${JSON.stringify({ accession: 'A', seenAt: 1 })}\nnot json\n`);
    const { entries, skipped } = readStateNdjson(p);
    expect(entries).toHaveLength(1);
    expect(skipped).toBeGreaterThanOrEqual(1);
  });

  it('N appends produce exactly N lines (no full rewrite / duplication)', () => {
    const p = join(dir, 's.ndjson');
    for (let i = 0; i < 4; i++) appendStateNdjson(p, [{ accession: `A${i}`, seenAt: i }]);
    const lines = readFileSync(p, 'utf8').split('\n').filter(Boolean);
    expect(lines).toHaveLength(4);
    expect(new Set(lines.map(l => JSON.parse(l).accession)).size).toBe(4);
  });
});
