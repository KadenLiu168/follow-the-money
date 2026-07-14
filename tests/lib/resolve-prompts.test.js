import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { resolvePrompts } from '../../lib/prompts/resolve.js';

const REMOTE_BASE = 'https://example.com/prompts';

describe('resolvePrompts', () => {
  let dirs = [];
  function tmp() {
    const d = mkdtempSync(join(tmpdir(), 'ftm-rp-'));
    dirs.push(d);
    return d;
  }

  // Default to "offline" so no test accidentally performs a real network call.
  // Individual tests override `fetch` to exercise the remote tier.
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('offline by default');
      }),
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    for (const d of dirs) rmSync(d, { recursive: true, force: true });
    dirs = [];
  });

  it('prefers user copy over remote and repo (user>remote>repo priority)', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    writeFileSync(join(userDir, 'format-13f.md'), 'USER VERSION');
    writeFileSync(join(repoDir, 'format-13f.md'), 'REPO VERSION');
    const res = await resolvePrompts({
      names: ['format-13f.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    expect(res.format_13f.source).toBe('user');
    expect(res.format_13f.text).toBe('USER VERSION');
  });

  it('falls back to remote copy when no user override and fetch returns 2xx', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      expect(url).toBe(join(REMOTE_BASE, 'format-13f.md'));
      return { ok: true, text: async () => 'REMOTE VERSION' };
    }));
    const res = await resolvePrompts({
      names: ['format-13f.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    expect(res.format_13f.source).toBe('remote');
    expect(res.format_13f.text).toBe('REMOTE VERSION');
  });

  it('falls back to repo when no user override and fetch throws (network error)', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    writeFileSync(join(repoDir, 'format-13f.md'), 'REPO VERSION');
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new Error('network down');
    }));
    const res = await resolvePrompts({
      names: ['format-13f.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    expect(res.format_13f.source).toBe('repo');
    expect(res.format_13f.text).toBe('REPO VERSION');
  });

  it('falls back to repo when no user override and fetch returns non-2xx (404)', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    writeFileSync(join(repoDir, 'format-13f.md'), 'REPO VERSION');
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404, text: async () => '404' })));
    const res = await resolvePrompts({
      names: ['format-13f.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    expect(res.format_13f.source).toBe('repo');
    expect(res.format_13f.text).toBe('REPO VERSION');
  });

  it('marks missing when user/repo empty and fetch fails', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new Error('network down');
    }));
    const res = await resolvePrompts({
      names: ['format-13f.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    expect(res.format_13f.source).toBe('missing');
    expect(res.format_13f.text).toBe('');
  });

  it('keys use underscore and drop .md extension', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    writeFileSync(join(repoDir, 'digest-intro.md'), 'x');
    const res = await resolvePrompts({
      names: ['digest-intro.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    expect(res).toHaveProperty('digest_intro');
    expect(res.digest_intro.source).toBe('repo');
    expect(res.digest_intro.text).toBe('x');
  });

  it('reports repo for every prompt when only the repo dir has files', async () => {
    const userDir = tmp();
    const repoDir = tmp();
    writeFileSync(join(repoDir, 'digest-intro.md'), 'a');
    writeFileSync(join(repoDir, 'format-13f.md'), 'b');
    writeFileSync(join(repoDir, 'format-13dg.md'), 'c');
    writeFileSync(join(repoDir, 'format-alert.md'), 'd');
    writeFileSync(join(repoDir, 'translate.md'), 'e');
    const res = await resolvePrompts({
      names: ['digest-intro.md', 'format-13f.md', 'format-13dg.md', 'format-alert.md', 'translate.md'],
      userDir,
      repoDir,
      remoteBaseUrl: REMOTE_BASE,
    });
    for (const key of ['digest_intro', 'format_13f', 'format_13dg', 'format_alert', 'translate']) {
      expect(res[key].source).toBe('repo');
      expect(res[key].text).toBeTruthy();
    }
  });
});
