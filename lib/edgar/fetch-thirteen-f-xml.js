// SEC 13F filings store the cover page (`primaryDocument` from the submissions
// API) and the <informationTable> as separate files in the filing directory.
// We resolve the real infoTable by fetching index.json and preferring the
// canonical `form13fInfoTable.xml`; only if that is absent do we fall back to
// the largest .xml. We NEVER fall back to `primaryDocument` (the cover page),
// which contains no holdings.

import { edgarDocUrl } from './archive-url.js';

const CANONICAL_INFO_TABLE = 'form13finfotable.xml';

export async function fetchThirteenFXml(httpClient, cik, accessionNumber, primaryDocument) {

  // Try to discover the real infoTable via the filing directory index.
  const indexUrl = edgarDocUrl(cik, accessionNumber, 'index.json');
  let infoTableFile = null;
  try {
    const indexRes = await httpClient.fetch(indexUrl);
    if (indexRes.ok) {
      const idx = await indexRes.json();
      const items = idx?.directory?.item ?? [];
      const xmlFiles = items.filter(i => i.name?.endsWith('.xml') && i.size > 0);
      // 1.1 Prefer the canonical infoTable filename (case-insensitive) before
      // any size heuristic — the cover page may be larger than the infoTable.
      const canonical = xmlFiles.find(i => i.name.toLowerCase() === CANONICAL_INFO_TABLE);
      if (canonical) {
        infoTableFile = canonical.name;
      } else if (xmlFiles.length > 0) {
        // 1.2 Largest-.xml heuristic only as a fallback when canonical absent.
        xmlFiles.sort((a, b) => b.size - a.size);
        infoTableFile = xmlFiles[0].name;
      }
      // 1.3 No usable .xml in index.json -> leave null; we throw below.
      // `primaryDocument` (the cover page) is intentionally NOT a fallback.
    }
  } catch {
    // index.json unavailable (older filings, network blip) -> no infoTableFile;
    // we throw below rather than parsing the cover page as holdings.
  }

  if (!infoTableFile) {
    throw new Error(
      `13F infoTable file not found for accession ${accessionNumber}: ` +
      `no ${CANONICAL_INFO_TABLE} and no fallback .xml in index.json ` +
      `(primaryDocument is a cover page and not a holdings source)`
    );
  }

  const res = await httpClient.fetch(edgarDocUrl(cik, accessionNumber, infoTableFile));
  if (!res.ok) throw new Error(`13F XML HTTP ${res.status} for ${infoTableFile}`);
  return res.text();
}
