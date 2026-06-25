import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { writeManifest } from './manifest.js';

function yearFile(feedDir, year) { return join(feedDir, `${year}.ndjson`); }

export function append13DFiling(feedDir, manifest, entry) {
  const year = String(new Date(entry.filingDate + 'T00:00:00Z').getUTCFullYear());
  mkdirSync(feedDir, { recursive: true });
  const file = yearFile(feedDir, year);
  const existing = existsSync(file) ? readFileSync(file, 'utf8') : '';
  const next = (existing.endsWith('\n') || !existing ? existing : existing + '\n') + JSON.stringify(entry) + '\n';
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, next);
  renameSync(tmp, file);

  const y = manifest.years[year] ?? { file: `feed-13dg/${year}.ndjson`, count: 0, firstDate: entry.filingDate, lastDate: entry.filingDate };
  y.count = (y.count ?? 0) + 1;
  y.firstDate = entry.filingDate < (y.firstDate ?? entry.filingDate) ? entry.filingDate : y.firstDate;
  y.lastDate = entry.filingDate > (y.lastDate ?? entry.filingDate) ? entry.filingDate : y.lastDate;
  manifest.years[year] = y;
  manifest.currentYear = Math.max(Number(year), manifest.currentYear ?? Number(year));
  writeManifest(feedDir, manifest);
}

export function read13DFilings(feedDir, manifest, { years } = {}) {
  const currentYear = manifest.currentYear ?? new Date().getUTCFullYear();
  const targetYears = years ?? [currentYear, currentYear - 1];
  const out = [];
  for (const y of targetYears) {
    const file = yearFile(feedDir, y);
    if (!existsSync(file)) continue;
    for (const line of readFileSync(file, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { out.push(JSON.parse(line)); } catch { /* skip corrupt line */ }
    }
  }
  out.sort((a, b) => b.filingDate.localeCompare(a.filingDate));
  return out;
}

export function validateManifest(feedDir, manifest) {
  const warnings = [];
  for (const [year, meta] of Object.entries(manifest.years ?? {})) {
    const file = yearFile(feedDir, year);
    if (!existsSync(file)) { warnings.push(`${year}: file missing`); continue; }
    const actual = readFileSync(file, 'utf8').split('\n').filter(Boolean).length;
    if (actual !== meta.count) warnings.push(`${year}: manifest says ${meta.count}, file has ${actual}`);
  }
  return { ok: warnings.length === 0, warnings };
}