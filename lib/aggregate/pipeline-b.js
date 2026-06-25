import { fetchThirteenDGSearch } from '../edgar/fetch-thirteen-dg-search.js';
import { parseThirteenDG } from '../parsers/thirteen-dg.js';
import { readManifest } from '../store/manifest.js';
import { append13DFiling } from '../store/feed-ndjson.js';
import { readStateNdjson, appendStateNdjson } from '../store/state-ndjson.js';

const FORMS = ['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'];

function isoDay(d) { return d.toISOString().slice(0, 10); }

export async function runPipelineB({ httpClient, config, feedDir, statePath, lookbackDays = 3 }) {
  if (!config.thirteenDG.enabled) return { added: 0, errors: [] };
  const today = new Date();
  const start = new Date(today.getTime() - lookbackDays * 86400000);
  const startDate = isoDay(start), endDate = isoDay(today);
  const manifest = readManifest(feedDir);
  const seen = new Set(readStateNdjson(statePath).map(e => e.accession));
  const errors = [];
  let added = 0;
  const newEntries = [];

  for (const formType of FORMS) {
    try {
      const hits = await fetchThirteenDGSearch(httpClient, { startDate, endDate, formType });
      for (const h of hits) {
        const s = h._source;
        const accession = s.adsh;
        if (seen.has(accession)) continue;
        const cikNoPad = String(parseInt(s.ciks[0], 10));
        const accNoDash = accession.replace(/-/g, '');
        const docUrl = `https://www.sec.gov/Archives/edgar/data/${cikNoPad}/${accNoDash}/primary_doc.html`;
        const res = await httpClient.fetch(docUrl);
        if (!res.ok) throw new Error(`primary doc HTTP ${res.status}`);
        const html = await res.text();
        const parsed = parseThirteenDG(html, { formType });
        newEntries.push({
          filerCik: String(s.ciks[0]).padStart(10, '0'),
          filerName: (s.display_names?.[0]) ?? 'UNKNOWN',
          issuerCik: String(s.ciks[1] ?? '').padStart(10, '0'),
          issuerName: parsed.issuerName,
          issuerTicker: parsed.issuerTicker || (s.tickers?.[0] ?? ''),
          formType,
          filingDate: s.file_date,
          ownershipPercent: parsed.ownershipPercent,
          sharesOwned: parsed.sharesOwned,
          intent: parsed.intent,
          accessionNumber: accession,
          primaryDocUrl: docUrl,
        });
      }
    } catch (err) {
      errors.push({ formType, error: err.message });
    }
  }

  for (const entry of newEntries) {
    append13DFiling(feedDir, manifest, entry);
    added++;
  }
  if (newEntries.length > 0) {
    appendStateNdjson(statePath, newEntries.map(e => ({ accession: e.accessionNumber, seenAt: Date.now() })));
  }
  return { added, errors };
}
