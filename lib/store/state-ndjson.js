import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync, appendFileSync, openSync, readSync, closeSync, statSync } from 'node:fs';
import { dirname } from 'node:path';

// If the existing file does not end with a newline, the first appended line
// must be prefixed with one so lines stay separable. O(1): only the last byte
// is read, never the whole file.
function needsLeadingNewline(path) {
  try {
    const size = statSync(path).size;
    if (size === 0) return false;
    const buf = Buffer.alloc(1);
    const fd = openSync(path, 'r');
    try { readSync(fd, buf, 0, 1, size - 1); } finally { closeSync(fd); }
    return buf[0] !== 0x0a; // 0x0a == '\n'
  } catch {
    return false;
  }
}

export function readStateNdjson(path) {
  if (!existsSync(path)) return { entries: [], skipped: 0 };
  const entries = [];
  let skipped = 0;
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try { entries.push(JSON.parse(line)); } catch { skipped++; }
  }
  return { entries, skipped };
}

export function appendStateNdjson(path, entries) {
  if (!Array.isArray(entries) || entries.length === 0) return;
  mkdirSync(dirname(path), { recursive: true });
  const prefix = needsLeadingNewline(path) ? '\n' : '';
  // O(1) append: a single serialized block is appended via O_APPEND. No full
  // read/rewrite of the existing file.
  appendFileSync(path, prefix + entries.map(e => JSON.stringify(e)).join('\n') + '\n');
}
