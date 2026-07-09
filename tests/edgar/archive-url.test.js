import { describe, it, expect } from 'vitest';
import { edgarArchiveUrl, edgarDocUrl } from '../../lib/edgar/archive-url.js';

describe('edgarArchiveUrl', () => {
  it('normalizes a zero-padded CIK', () => {
    expect(edgarArchiveUrl('0001067983', '0001067983-26-000123')).toBe(
      'https://www.sec.gov/Archives/edgar/data/1067983/000106798326000123',
    );
  });

  it('leaves an already-unpadded CIK unchanged', () => {
    expect(edgarArchiveUrl('1067983', '0001067983-26-000123')).toBe(
      'https://www.sec.gov/Archives/edgar/data/1067983/000106798326000123',
    );
  });
});

describe('edgarDocUrl', () => {
  it('appends the file name to the archive URL', () => {
    expect(edgarDocUrl('0001067983', '0001067983-26-000123', 'form13fInfoTable.xml')).toBe(
      'https://www.sec.gov/Archives/edgar/data/1067983/000106798326000123/form13fInfoTable.xml',
    );
  });
});
