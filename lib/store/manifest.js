import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { atomicWriteJSON } from './atomic-write.js';

const MANIFEST_FILE = 'manifest.json';
const DEFAULTS = () => ({ schemaVersion: 1, currentYear: new Date().getUTCFullYear(), years: {} });

export function readManifest(feedDir) {
  const p = join(feedDir, MANIFEST_FILE);
  if (!existsSync(p)) return DEFAULTS();
  try {
    const parsed = JSON.parse(readFileSync(p, 'utf8'));
    return { ...DEFAULTS(), ...parsed, years: parsed.years ?? {} };
  } catch {
    return DEFAULTS();
  }
}

export function writeManifest(feedDir, manifest) {
  mkdirSync(feedDir, { recursive: true });
  const p = join(feedDir, MANIFEST_FILE);
  atomicWriteJSON(p, manifest);
}