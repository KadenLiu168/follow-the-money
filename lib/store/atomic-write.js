import { writeFileSync, renameSync } from 'node:fs';

// Synchronous, crash-safe atomic write shared by the JSON store writers.
// Previously each writer duplicated this `tmp + writeFileSync + renameSync`
// block; centralizing it removes the drift risk. The temp file name matches
// the original inline pattern exactly (`${path}.${pid}.${Date.now()}.tmp`),
// and the rename(2) is atomic on POSIX so readers never see a torn file.
//
// NOTE: callers are responsible for ensuring the destination directory exists
// (the writers call `mkdirSync(dirname(path), { recursive: true })` first).
// This helper intentionally does NOT auto-create the directory so that a
// missing/unwritable destination surfaces as a thrown error rather than a
// silently created path.
function atomicWrite(path, content) {
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, content);
  renameSync(tmp, path);
}

export function atomicWriteJSON(path, obj) {
  atomicWrite(path, JSON.stringify(obj, null, 2));
}

export function atomicWriteText(path, str) {
  atomicWrite(path, str);
}
