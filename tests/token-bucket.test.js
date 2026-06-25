import { describe, it, expect } from 'vitest';
import { TokenBucket } from '../lib/token-bucket.js';

describe('TokenBucket', () => {
  it('throws if rate or capacity invalid', () => {
    expect(() => new TokenBucket(0, 1)).toThrow();
    expect(() => new TokenBucket(10, 0)).toThrow();
    expect(() => new TokenBucket(-1, 1)).toThrow();
  });

  it('allows up to capacity instant takes', async () => {
    const tb = new TokenBucket(1, 3);
    await Promise.all([tb.take(), tb.take(), tb.take()]);
    expect(true).toBe(true); // no throw
  });

  it('blocks the 4th take when capacity is 3', async () => {
    const tb = new TokenBucket(1, 3);
    await Promise.all([tb.take(), tb.take(), tb.take()]);
    const start = Date.now();
    await tb.take();
    expect(Date.now() - start).toBeGreaterThanOrEqual(900);
  });

  it('refills at the configured rate', async () => {
    const tb = new TokenBucket(20, 1); // 20/sec → one token every 50ms
    await tb.take();
    const start = Date.now();
    await tb.take();
    expect(Date.now() - start).toBeGreaterThanOrEqual(40);
    expect(Date.now() - start).toBeLessThan(200);
  });
});