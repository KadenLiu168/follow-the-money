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
});
