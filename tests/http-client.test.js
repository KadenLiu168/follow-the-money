import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { createHttpClient } from '../lib/http-client.js';
import { TokenBucket } from '../lib/token-bucket.js';

describe('HttpClient', () => {
  let bucket, client;
  beforeEach(() => {
    bucket = new TokenBucket(100, 100);
    client = createHttpClient({ userAgent: 'TestApp test@example.com', bucket });
    nock.disableNetConnect();
  });
  afterEach(() => {
    nock.cleanAll();
    nock.enableNetConnect();
  });

  it('adds User-Agent to every request', async () => {
    const scope = nock('https://example.com', {
      reqheaders: { 'user-agent': 'TestApp test@example.com' },
    })
      .get('/foo')
      .reply(200, { ok: true });
    const res = await client.fetch('https://example.com/foo');
    expect(await res.json()).toEqual({ ok: true });
    expect(scope.isDone()).toBe(true);
  });

  it('retries on 429 honoring Retry-After', async () => {
    nock('https://example.com').get('/bar').reply(429, '', { 'Retry-After': '0' });
    nock('https://example.com').get('/bar').reply(200, { ok: true });
    const res = await client.fetch('https://example.com/bar');
    expect(res.status).toBe(200);
  });

  it('retries 3× on network error then throws', async () => {
    nock('https://example.com').get('/baz').times(3).replyWithError('boom');
    await expect(client.fetch('https://example.com/baz')).rejects.toThrow(/boom|Failed/);
  });
});
