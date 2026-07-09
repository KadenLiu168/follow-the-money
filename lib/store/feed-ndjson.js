import { readFileSync, existsSync, mkdirSync, appendFileSync } from 'node:fs';
import { join } from 'node:path';
import { writeManifest } from './manifest.js';

function yearFile(feedDir, year) { return join(feedDir, `${year}.ndjson`); }

const FILING_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

// Derive the UTC year from a filingDate, or null if the date is invalid.
// Guards against writing a file keyed by `NaN` (e.g. "not-a-date" or
// "2026-13-45") which the manifest would silently drop.
function deriveYear(filingDate) {
  if (!FILING_DATE_RE.test(filingDate ?? '')) return null;
  const d = new Date(`${filingDate}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  return String(d.getUTCFullYear());
}

export function append13DFiling(feedDir, manifest, entry) {
  const year = deriveYear(entry.filingDate);
  if (year === null) {
    console.warn(`[feed-ndjson] skipping entry with invalid filingDate: ${JSON.stringify(entry.filingDate)}`);
    return manifest;
  }
  mkdirSync(feedDir, { recursive: true });
  const file = yearFile(feedDir, year);
  // O(1) append: a single line is appended via O_APPEND, so no full-file read
  // or rewrite happens. appendFileSync is atomic for the single written line
  // relative to other writers, preserving the crash-safety the old tmp+rename
  // pattern provided without paying the O(filesize) read cost.
  appendFileSync(file, JSON.stringify(entry) + '\n');

  const y = manifest.years[year] ?? { file: `feed-13dg/${year}.ndjson`, count: 0, firstDate: entry.filingDate, lastDate: entry.filingDate };
  y.count = (y.count ?? 0) + 1;
  y.firstDate = entry.filingDate < (y.firstDate ?? entry.filingDate) ? entry.filingDate : y.firstDate;
  y.lastDate = entry.filingDate > (y.lastDate ?? entry.filingDate) ? entry.filingDate : y.lastDate;
  manifest.years[year] = y;
  manifest.currentYear = Math.max(Number(year), manifest.currentYear ?? Number(year));
  writeManifest(feedDir, manifest);
  return manifest;
}

export function read13DFilings(feedDir, manifest, { years } = {}) {
  const currentYear = manifest.currentYear ?? new Date().getUTCFullYear();
  const targetYears = years ?? [currentYear, currentYear - 1];
  const entries = [];
  let skipped = 0;
  for (const y of targetYears) {
    const file = yearFile(feedDir, y);
    if (!existsSync(file)) continue;
    for (const line of readFileSync(file, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { entries.push(JSON.parse(line)); } catch { skipped++; }
    }
  }
  entries.sort((a, b) => b.filingDate.localeCompare(a.filingDate));
  return { entries, skipped };
}

export function validateManifest(feedDir, manifest) {
  const warnings = [];
  for (const [year, meta] of Object.entries(manifest.years ?? {})) {
    const file = yearFile(feedDir, year);
    if (!existsSync(file)) { warnings.push(`${year}: file missing`); continue; }
    let actual = 0, corrupt = 0;
    for (const line of readFileSync(file, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { JSON.parse(line); actual++; } catch { corrupt++; }
    }
    if (actual !== meta.count) warnings.push(`${year}: manifest says ${meta.count}, file has ${actual}`);
    if (corrupt > 0) warnings.push(`${year}: ${corrupt} corrupt line(s) skipped`);
  }
  return { ok: warnings.length === 0, warnings };
}
