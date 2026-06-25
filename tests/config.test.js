import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const configPath = join(__dirname, '..', 'config', 'default-sources.json');

describe('default-sources.json', () => {
  it('contains 8 CIKs', () => {
    const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
    expect(cfg.thirteenF).toHaveLength(8);
    for (const f of cfg.thirteenF) {
      expect(f.cik).toMatch(/^\d{10}$/);
      expect(f.name).toBeTruthy();
      expect(f.style).toBeTruthy();
    }
  });

  it('has 13D/G config enabled', () => {
    const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
    expect(cfg.thirteenDG.enabled).toBe(true);
    expect(cfg.thirteenDG.lookbackDays).toBeGreaterThan(0);
  });
});
