import { describe, it, expect } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { resolvePrompts } from '../../lib/prompts/resolve.js';

function hash(text) {
  return createHash('sha256').update(text).digest('hex').slice(0, 16);
}

describe('resolvePrompts', () => {
  it('prefers user copy over repo copy (user>repo priority)', () => {
    const userDir = mkdtempSync(join(tmpdir(), 'ftm-rp-user-'));
    const repoDir = mkdtempSync(join(tmpdir(), 'ftm-rp-repo-'));
    try {
      writeFileSync(join(userDir, 'format-13f.md'), 'USER VERSION');
      writeFileSync(join(repoDir, 'format-13f.md'), 'REPO VERSION');
      const res = resolvePrompts({ names: ['format-13f.md'], userDir, repoDir });
      expect(res.format_13f.source).toBe('user');
      expect(res.format_13f.text).toBe('USER VERSION');
      expect(res.format_13f.hash).toBe(hash('USER VERSION'));
    } finally {
      rmSync(userDir, { recursive: true, force: true });
      rmSync(repoDir, { recursive: true, force: true });
    }
  });

  it('falls back to repo copy when no user override', () => {
    const userDir = mkdtempSync(join(tmpdir(), 'ftm-rp-user2-'));
    const repoDir = mkdtempSync(join(tmpdir(), 'ftm-rp-repo2-'));
    try {
      writeFileSync(join(repoDir, 'format-13f.md'), 'REPO ONLY');
      const res = resolvePrompts({ names: ['format-13f.md'], userDir, repoDir });
      expect(res.format_13f.source).toBe('repo');
      expect(res.format_13f.text).toBe('REPO ONLY');
    } finally {
      rmSync(userDir, { recursive: true, force: true });
      rmSync(repoDir, { recursive: true, force: true });
    }
  });

  it('keys use underscore and drop .md extension', () => {
    const userDir = mkdtempSync(join(tmpdir(), 'ftm-rp-user3-'));
    const repoDir = mkdtempSync(join(tmpdir(), 'ftm-rp-repo3-'));
    try {
      writeFileSync(join(repoDir, 'digest-intro.md'), 'x');
      const res = resolvePrompts({ names: ['digest-intro.md'], userDir, repoDir });
      expect(res).toHaveProperty('digest_intro');
      expect(res.digest_intro.hash).toBe(hash('x'));
    } finally {
      rmSync(userDir, { recursive: true, force: true });
      rmSync(repoDir, { recursive: true, force: true });
    }
  });

  it('reports repo for every prompt when only the repo dir has files', () => {
    const userDir = mkdtempSync(join(tmpdir(), 'ftm-rp-user4-'));
    const repoDir = mkdtempSync(join(tmpdir(), 'ftm-rp-repo4-'));
    try {
      writeFileSync(join(repoDir, 'digest-intro.md'), 'a');
      writeFileSync(join(repoDir, 'format-13f.md'), 'b');
      writeFileSync(join(repoDir, 'format-13dg.md'), 'c');
      writeFileSync(join(repoDir, 'format-alert.md'), 'd');
      writeFileSync(join(repoDir, 'translate.md'), 'e');
      const res = resolvePrompts({
        names: [
          'digest-intro.md',
          'format-13f.md',
          'format-13dg.md',
          'format-alert.md',
          'translate.md',
        ],
        userDir,
        repoDir,
      });
      for (const key of [
        'digest_intro',
        'format_13f',
        'format_13dg',
        'format_alert',
        'translate',
      ]) {
        expect(res[key].source).toBe('repo');
        expect(res[key].hash).toMatch(/^[0-9a-f]{16}$/);
      }
    } finally {
      rmSync(userDir, { recursive: true, force: true });
      rmSync(repoDir, { recursive: true, force: true });
    }
  });
});
