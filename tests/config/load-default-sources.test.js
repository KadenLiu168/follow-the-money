import { describe, it, expect } from 'vitest';
import { loadDefaultSources } from '../../lib/config/load-default-sources.js';

describe('loadDefaultSources', () => {
  it('parses config/default-sources.json into an object with a thirteenF array', () => {
    const cfg = loadDefaultSources();
    expect(cfg).toBeTypeOf('object');
    expect(Array.isArray(cfg.thirteenF)).toBe(true);
  });
});
