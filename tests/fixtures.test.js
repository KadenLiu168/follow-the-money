// tests/fixtures.test.js
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fx = join(__dirname, 'fixtures');

describe('fixtures load', () => {
  it('every fixture is parseable', () => {
    const files = [
      'submissions-cik-0001067983.json',
      'search-13dg.json',
      'feed-13f.json',
      'feed-13dg/manifest.json',
      'feed-13dg/2025.ndjson',
      'feed-13dg/2026.ndjson',
      'state-13f.json',
      'config.json',
    ];
    for (const f of files) {
      const content = readFileSync(join(fx, f), 'utf8');
      if (f.endsWith('.ndjson')) {
        const lines = content.split('\n').filter(Boolean);
        expect(lines.length).toBeGreaterThan(0);
        for (const line of lines) JSON.parse(line);
      } else {
        JSON.parse(content);
      }
    }
  });
});
