import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import nock from 'nock';

const runPipelineAMock = vi.fn();
const runPipelineBMock = vi.fn();

vi.mock('../../lib/aggregate/pipeline-a.js', () => ({
  runPipelineA: (...args) => runPipelineAMock(...args),
}));
vi.mock('../../lib/aggregate/pipeline-b.js', () => ({
  runPipelineB: (...args) => runPipelineBMock(...args),
}));

describe('aggregate.js (mocked, execSync)', () => {
  beforeEach(() => {
    process.env.SEC_EDGAR_USER_AGENT = 'T t@e.com';
    nock.disableNetConnect();
    runPipelineAMock.mockReset();
    runPipelineBMock.mockReset();
  });
  afterEach(() => {
    nock.cleanAll();
    nock.enableNetConnect();
    vi.restoreAllMocks();
  });

  it('fails with clear error if env var missing', async () => {
    delete process.env.SEC_EDGAR_USER_AGENT;
    const { execSync } = await import('node:child_process');
    expect(() => execSync('node scripts/aggregate.js', { stdio: 'pipe' })).toThrow(
      /SEC_EDGAR_USER_AGENT/,
    );
  });

  it('exits 0 on partial success (pipeline A errored, pipeline B added 3)', async () => {
    runPipelineAMock.mockResolvedValue({ added: 0, errors: [{ cik: 'x', error: 'fail' }] });
    runPipelineBMock.mockResolvedValue({ added: 3, errors: [] });

    const { main } = await import('../../scripts/aggregate.js');
    const exitSpy = vi.spyOn(process, 'exit').mockImplementation((code) => {
      throw new Error(`__exit_${code}__`);
    });
    await expect(main()).resolves.toBeUndefined();
    const codes = exitSpy.mock.calls.map((c) => c[0]);
    expect(codes).not.toContain(1);
  });
});
