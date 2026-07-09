import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { atomicWriteJSON } from './atomic-write.js';

const DEFAULTS = { lastUpdated: '1970-01-01T00:00:00.000Z', seenFilings: {} };

export function readStateJson(path) {
  if (!existsSync(path)) return structuredClone(DEFAULTS);
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8'));
    return { ...DEFAULTS, ...parsed };
  } catch {
    return structuredClone(DEFAULTS);
  }
}

export function writeStateJson(path, state) {
  mkdirSync(dirname(path), { recursive: true });
  atomicWriteJSON(path, state);
}