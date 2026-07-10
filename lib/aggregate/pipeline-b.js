import { fetchThirteenDGSearch } from '../edgar/fetch-thirteen-dg-search.js';
import { parseThirteenDG } from '../parsers/thirteen-dg.js';
import { readManifest } from '../store/manifest.js';
import { append13DFiling } from '../store/feed-ndjson.js';
import { readStateNdjson, appendStateNdjson } from '../store/state-ndjson.js';
import { edgarDocUrl } from '../edgar/archive-url.js';

const FORMS = ['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'];

function isoDay(d) {
  return d.toISOString().slice(0, 10);
}

export async function runPipelineB({ httpClient, config, feedDir, statePath, lookbackDays = 3 }) {
  if (!config.thirteenDG.enabled) return { added: 0, errors: [] };
  const today = new Date();
  const start = new Date(today.getTime() - lookbackDays * 86400000);
  const startDate = isoDay(start),
    endDate = isoDay(today);
  const manifest = readManifest(feedDir);
  const seen = new Set(readStateNdjson(statePath).entries.map((e) => e.accession));
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
        const cik = String(parseInt(s.ciks[0], 10));
        // Filename varies (e.g. sc13d.htm, sc13g.htm, primary_doc.html);
        // resolve via index.json — pick the largest .htm/.html.
        let docUrl = edgarDocUrl(cik, accession, 'primary_doc.html');
        try {
          const indexRes = await httpClient.fetch(edgarDocUrl(cik, accession, 'index.json'));
          if (indexRes.ok) {
            const idx = await indexRes.json();
            const htmls = (idx?.directory?.item ?? [])
              .filter((i) => /\.(htm|html|txt)$/i.test(i.name ?? '') && i.size > 0)
              .filter((i) => !/-index(-headers)?\.html?$/i.test(i.name));
            if (htmls.length > 0) {
              htmls.sort((a, b) => b.size - a.size);
              docUrl = edgarDocUrl(cik, accession, htmls[0].name);
            }
          }
        } catch {
          /* fall through to primary_doc.html */
        }
        const res = await httpClient.fetch(docUrl);
        if (!res.ok) throw new Error(`primary doc HTTP ${res.status} for ${docUrl}`);
        const html = await res.text();
        const parsed = parseThirteenDG(html, { formType });
        newEntries.push({
          filerCik: String(s.ciks[0]).padStart(10, '0'),
          filerName: s.display_names?.[0] ?? 'UNKNOWN',
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
      console.error(`[pipeline-b] ${formType}: ${err.message}`);
      errors.push({ formType, error: err.message });
    }
  }

  for (const entry of newEntries) {
    append13DFiling(feedDir, manifest, entry);
    added++;
  }
  if (newEntries.length > 0) {
    appendStateNdjson(
      statePath,
      newEntries.map((e) => ({ accession: e.accessionNumber, seenAt: Date.now() })),
    );
  }
  return { added, errors };
}
