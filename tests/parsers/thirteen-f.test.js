import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseThirteenF } from '../../lib/parsers/thirteen-f.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const xml = readFileSync(join(__dirname, '../fixtures/form13fData.xml'), 'utf8');

describe('parseThirteenF', () => {
  it('parses holdings with voting authority split', () => {
    const r = parseThirteenF(xml);
    expect(r).toHaveLength(1);
    expect(r[0]).toMatchObject({
      cusip: '037833100',
      issuerName: 'APPLE INC',
      valueUsd: 58200000000,
      shares: 300000000,
      votingAuthority: { sole: 300000000, shared: 0, none: 0 },
    });
  });

  it('returns [] on empty <informationTable/>', () => {
    expect(parseThirteenF('<?xml version="1.0"?><informationTable/>')).toEqual([]);
  });
});
