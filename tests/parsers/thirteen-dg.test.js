import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseThirteenDG } from '../../lib/parsers/thirteen-dg.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const html13d = readFileSync(join(__dirname, '../fixtures/13d-primary-doc.html'), 'utf8');
const html13g = readFileSync(join(__dirname, '../fixtures/13g-primary-doc.html'), 'utf8');

describe('parseThirteenDG', () => {
  it('parses 13D and tags intent=active by form type', () => {
    const r = parseThirteenDG(html13d, { formType: 'SC 13D' });
    expect(r).toMatchObject({
      issuerName: 'Jet.AI Inc',
      issuerTicker: 'JTAI',
      ownershipPercent: 6.8,
      sharesOwned: 4500000,
      intent: 'active',
    });
  });

  it('parses 13G and tags intent=passive by form type', () => {
    const r = parseThirteenDG(html13g, { formType: 'SC 13G' });
    expect(r.issuerName).toBe('Activision Blizzard Inc');
    expect(r.intent).toBe('passive');
  });

  it('SC 13D/A still maps to active', () => {
    const r = parseThirteenDG(html13d, { formType: 'SC 13D/A' });
    expect(r.intent).toBe('active');
  });

  it('SC 13G/A maps to passive', () => {
    const r = parseThirteenDG(html13g, { formType: 'SC 13G/A' });
    expect(r.intent).toBe('passive');
  });

  it('throws on unknown form type', () => {
    expect(() => parseThirteenDG(html13d, { formType: '10-K' })).toThrow(/invalid formType/);
  });

  it('parses real SEC 13D HTML (parens-wrapped Title Case labels)', async () => {
    // Fetch a real 13D filing and parse it.
    const { createHttpClient } = await import('../../lib/http-client.js');
    const { TokenBucket } = await import('../../lib/token-bucket.js');
    const client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    const url =
      'https://www.sec.gov/Archives/edgar/data/1474627/000147793224008147/tekhill_sc13da.htm';
    const res = await client.fetch(url);
    if (!res.ok) return; // skip if SEC is unavailable
    const html = await res.text();
    const r = parseThirteenDG(html, { formType: 'SC 13D/A' });
    expect(r.issuerName).toBe('Newegg Commerce, Inc.');
    expect(r.intent).toBe('active');
  }, 10000);
});
