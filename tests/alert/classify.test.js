import { describe, it, expect } from 'vitest';
import { classify, ALERT_FORMS } from '../../lib/alert/classify.js';

describe('classify', () => {
  it('SC 13D and 13D/A are alert', () => {
    expect(classify({ formType: 'SC 13D' })).toBe('alert');
    expect(classify({ formType: 'SC 13D/A' })).toBe('alert');
  });
  it('SC 13G and 13G/A are digest', () => {
    expect(classify({ formType: 'SC 13G' })).toBe('digest');
    expect(classify({ formType: 'SC 13G/A' })).toBe('digest');
  });
  it('ALERT_FORMS contains exactly 13D/13D-A', () => {
    expect([...ALERT_FORMS].sort()).toEqual(['SC 13D', 'SC 13D/A']);
  });
});
