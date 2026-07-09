// Stdout-only delivery (see openspec/changes/stdout-only-delivery/).
// Reads --text <string> or --file <path> and writes the content to stdout.
// Does not read config, does not load .env, makes no network calls.

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url));

// Resolve a --file argument, refusing anything that escapes the repo root
// (e.g. ../../etc/passwd or an absolute /etc/passwd).
export function resolveSafePath(p) {
  const resolved = resolve(REPO_ROOT, p);
  if (!resolved.startsWith(REPO_ROOT)) {
    throw new Error(`path escapes repo root: ${p}`);
  }
  return resolved;
}

const args = process.argv.slice(2);
const textIdx = args.indexOf('--text');
const fileIdx = args.indexOf('--file');
const textLiteral = textIdx >= 0 ? args[textIdx + 1] : '';
const filePath = fileIdx >= 0 ? args[fileIdx + 1] : '';

let text = textLiteral;
if (!text && filePath) {
  try {
    text = readFileSync(resolveSafePath(filePath), 'utf8');
  } catch (err) {
    console.error(`ERROR: failed to read ${filePath}: ${err.message}`);
    process.exit(1);
  }
}

if (!text) {
  console.error('ERROR: --text or --file required');
  process.exit(1);
}

console.log(text);
