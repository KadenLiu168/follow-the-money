import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseThirteenDG } from '../../lib/parsers/thirteen-dg.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const html13d = readFileSync(join(__dirname, '../fixtures/13d-primary-doc.html'), 'utf8');
const html13g = readFileSync(join(__dirname, '../fixtures/13g-primary-doc.html'), 'utf8');
const html13dHtmlShape = readFileSync(join(__dirname, '../fixtures/13d-html-shape.html'), 'utf8');

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

  it('parses HTML-shape 13D (Percent of Class 6.8% / 1,234,567 shares)', () => {
    // Regression guard for D7: modern EDGAR 13D/G filings are HTML-shaped.
    // The old parser returned ownershipPercent:0 (Number("6.8%")=NaN) and
    // sharesOwned:1 (zero-width lookahead truncated "1,234,567" to "1").
    const r = parseThirteenDG(html13dHtmlShape, { formType: 'SC 13D' });
    expect(r.ownershipPercent).toBe(6.8);
    expect(r.sharesOwned).toBe(1234567);
    expect(r.issuerName).toBe('Jet.AI Inc');
    expect(r.issuerTicker).toBe('JTAI');
    expect(r.intent).toBe('active');
  });

  it('ignores trailing label text and non-numeric raw for numeric fields', () => {
    // Covers spec scenarios: trailing label after shares is ignored, and a
    // non-numeric percent raw (e.g. "--") yields 0 rather than NaN.
    const html = [
      '<p>Aggregate Amount Beneficially Owned<br>1,234,567 Shared Voting Power 0</p>',
      '<p>Percent of Class<br>--</p>',
    ].join('');
    const r = parseThirteenDG(html, { formType: 'SC 13D' });
    expect(r.sharesOwned).toBe(1234567);
    expect(r.ownershipPercent).toBe(0);
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
