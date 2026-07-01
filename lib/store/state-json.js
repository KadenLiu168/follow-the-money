import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

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
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, JSON.stringify(state, null, 2));
  renameSync(tmp, path);
}