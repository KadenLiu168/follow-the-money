// Single shared loader for config/default-sources.json.
// Replaces the three ad-hoc readers (readFileSync+JSON.parse in
// aggregate.js / verify-edgar.js, and the static import attribute in
// prepare-digest.js) with one source of truth.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export function loadDefaultSources() {
  const url = new URL('../../config/default-sources.json', import.meta.url);
  return JSON.parse(readFileSync(fileURLToPath(url), 'utf8'));
}
