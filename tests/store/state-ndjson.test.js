import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readStateNdjson, appendStateNdjson } from '../../lib/store/state-ndjson.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('state-ndjson', () => {
  it('returns [] when file missing', () => {
    expect(readStateNdjson(join(dir, 'missing.ndjson'))).toEqual([]);
  });

  it('appends entries and round-trips', () => {
    const p = join(dir, 's.ndjson');
    appendStateNdjson(p, [{ accession: 'A', seenAt: 1 }]);
    appendStateNdjson(p, [{ accession: 'B', seenAt: 2 }]);
    expect(readStateNdjson(p)).toEqual([
      { accession: 'A', seenAt: 1 },
      { accession: 'B', seenAt: 2 },
    ]);
  });

  it('skips blank lines on read', () => {
    const p = join(dir, 's.ndjson');
    appendStateNdjson(p, [{ accession: 'A', seenAt: 1 }]);
    expect(readStateNdjson(p).length).toBe(1);
  });
});