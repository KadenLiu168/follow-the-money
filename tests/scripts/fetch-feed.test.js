import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoCwd = join(__dirname, '..', '..');

let targetDir;
beforeEach(() => {
  targetDir = mkdtempSync(join(tmpdir(), 'ftm-fetch-cli-'));
  vi.resetModules();
});
afterEach(() => {
  rmSync(targetDir, { recursive: true, force: true });
  vi.restoreAllMocks();
});

describe('scripts/fetch-feed.js (defaultTargetDir)', () => {
  it('resolves macOS default to ~/Library/Caches/follow-the-money/feed/', async () => {
    vi.stubEnv('FOLLOW_THE_MONEY_FEED_DIR', '');
    Object.defineProperty(process, 'platform', { value: 'darwin', configurable: true });
    vi.stubEnv('HOME', '/Users/test');
    const { defaultTargetDir } = await import('../../scripts/fetch-feed.js');
    expect(defaultTargetDir()).toBe('/Users/test/Library/Caches/follow-the-money/feed');
  });

  it('resolves Linux default using XDG_CACHE_HOME when set', async () => {
    vi.stubEnv('FOLLOW_THE_MONEY_FEED_DIR', '');
    Object.defineProperty(process, 'platform', { value: 'linux', configurable: true });
    vi.stubEnv('XDG_CACHE_HOME', '/custom/cache');
    vi.stubEnv('HOME', '/home/test');
    const { defaultTargetDir } = await import('../../scripts/fetch-feed.js');
    expect(defaultTargetDir()).toBe('/custom/cache/follow-the-money/feed');
  });

  it('resolves Linux default to ~/.cache/follow-the-money/feed/ when XDG_CACHE_HOME unset', async () => {
    vi.stubEnv('FOLLOW_THE_MONEY_FEED_DIR', '');
    Object.defineProperty(process, 'platform', { value: 'linux', configurable: true });
    vi.stubEnv('XDG_CACHE_HOME', '');
    vi.stubEnv('HOME', '/home/test');
    const { defaultTargetDir } = await import('../../scripts/fetch-feed.js');
    expect(defaultTargetDir()).toBe('/home/test/.cache/follow-the-money/feed');
  });

  it('respects FOLLOW_THE_MONEY_FEED_DIR env var over platform default', async () => {
    vi.stubEnv('FOLLOW_THE_MONEY_FEED_DIR', '/override/path');
    Object.defineProperty(process, 'platform', { value: 'linux', configurable: true });
    const { defaultTargetDir } = await import('../../scripts/fetch-feed.js');
    expect(defaultTargetDir()).toBe('/override/path');
  });
});

describe('scripts/fetch-feed.js (CLI execSync)', () => {
  it('exits 0 with ok=true JSON on successful fetch', async () => {
    vi.stubEnv('FOLLOW_THE_MONEY_FEED_DIR', targetDir);
    const fetchFeedMock = vi.fn().mockResolvedValue({
      ok: true,
      filesWritten: ['feed-13f.json', 'state-13f.json'],
      partialFilesWritten: [],
    });
    vi.doMock('../../lib/fetch/fetch-feed.js', () => ({
      fetchFeed: fetchFeedMock,
    }));
    const { main } = await import('../../scripts/fetch-feed.js');
    const writeSpy = vi.spyOn(process.stdout, 'write').mockImplementation(() => true);
    vi.spyOn(process, 'exit').mockImplementation((code) => {
      throw new Error(`__exit_${code}__`);
    });
    await expect(main()).rejects.toThrow('__exit_0__');
    expect(fetchFeedMock).toHaveBeenCalledWith(expect.objectContaining({ targetDir }));
    const out = writeSpy.mock.calls.map((c) => c[0]).join('');
    const parsed = JSON.parse(out);
    expect(parsed.ok).toBe(true);
  });

  it('exits 1 with ok=false JSON on failed fetch', async () => {
    vi.stubEnv('FOLLOW_THE_MONEY_FEED_DIR', targetDir);
    vi.doMock('../../lib/fetch/fetch-feed.js', () => ({
      fetchFeed: vi.fn().mockResolvedValue({
        ok: false,
        reason: 'static_fetch_failed: feed-13f.json: HTTP 404',
        filesWritten: [],
        partialFilesWritten: [],
      }),
    }));
    const { main } = await import('../../scripts/fetch-feed.js');
    const writeSpy = vi.spyOn(process.stdout, 'write').mockImplementation(() => true);
    vi.spyOn(process, 'exit').mockImplementation((code) => {
      throw new Error(`__exit_${code}__`);
    });
    await expect(main()).rejects.toThrow('__exit_1__');
    const out = writeSpy.mock.calls.map((c) => c[0]).join('');
    const parsed = JSON.parse(out);
    expect(parsed.ok).toBe(false);
    expect(parsed.reason).toMatch(/404/);
  });
});

describe('scripts/fetch-feed.js (--print-dir)', () => {
  it('prints defaultTargetDir() and exits 0 with no network I/O', async () => {
    const out = execSync('node scripts/fetch-feed.js --print-dir', {
      cwd: repoCwd,
      encoding: 'utf8',
    });
    const { defaultTargetDir } = await import('../../scripts/fetch-feed.js');
    expect(out.trim()).toBe(defaultTargetDir());
  });

  it('honors FOLLOW_THE_MONEY_FEED_DIR override (single source of truth)', () => {
    const custom = mkdtempSync(join(tmpdir(), 'ftm-printdir-'));
    try {
      const out = execSync('node scripts/fetch-feed.js --print-dir', {
        cwd: repoCwd,
        env: { ...process.env, FOLLOW_THE_MONEY_FEED_DIR: custom },
        encoding: 'utf8',
      });
      expect(out.trim()).toBe(custom);
    } finally {
      rmSync(custom, { recursive: true, force: true });
    }
  });

  it('does not invoke fetchFeed when --print-dir is passed', async () => {
    const fetchFeedMock = vi.fn();
    vi.doMock('../../lib/fetch/fetch-feed.js', () => ({ fetchFeed: fetchFeedMock }));
    const { main } = await import('../../scripts/fetch-feed.js');
    const writeSpy = vi.spyOn(process.stdout, 'write').mockImplementation(() => true);
    await main(['--print-dir']);
    expect(fetchFeedMock).not.toHaveBeenCalled();
    expect(writeSpy).toHaveBeenCalled();
  });
});
