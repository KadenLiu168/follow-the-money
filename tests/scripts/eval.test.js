// tests/scripts/eval.test.js
import { describe, it, expect } from 'vitest';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('eval.js (CI stub mode)', () => {
  it('runs and reports results', () => {
    // Use spawnSync (not execSync) so non-zero exit doesn't throw — the
    // CI stub is expected to fail some checks; the smoke test only
    // asserts the runner framework produces a "Result:" line.
    const result = spawnSync('node', ['scripts/eval.js'], {
      cwd: join(__dirname, '..', '..'),
      encoding: 'utf8',
    });
    expect(result.stdout).toMatch(/Result: \d+ passed, \d+ failed/);
  });
});
