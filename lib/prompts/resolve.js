import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';

function toKey(name) {
  return name.replace(/\.md$/, '').replace(/-/g, '_');
}

function hashContent(text) {
  return createHash('sha256').update(text).digest('hex').slice(0, 16);
}

// Resolve prompt files by user > repo priority. This is the SINGLE place that
// encodes the override rule (replaces the doc-only convention in
// references/prompt-customization.md). Returns a map keyed by file name with
// `.md` stripped and hyphens → underscores (e.g. "format-13f.md" → "format_13f").
export function resolvePrompts({ names, userDir, repoDir }) {
  const result = {};
  for (const name of names) {
    const key = toKey(name);
    const userPath = join(userDir, name);
    const repoPath = join(repoDir, name);
    const source = existsSync(userPath) ? 'user' : 'repo';
    const path = source === 'user' ? userPath : repoPath;
    const text = existsSync(path) ? readFileSync(path, 'utf8') : '';
    result[key] = { source, text, hash: hashContent(text) };
  }
  return result;
}
