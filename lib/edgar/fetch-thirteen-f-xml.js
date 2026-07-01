// SEC 13F filings store the cover page and the <informationTable> as separate
// files in the filing directory. `primaryDocument` from the submissions API
// points to the cover page; the actual infoTable is a sibling. We resolve
// the real infoTable by fetching index.json and picking the largest .xml
// (the cover page is always smaller, ~5KB; infoTable is 10KB+ for any
// meaningful filer). Falls back to primaryDocument if index.json is missing.

export async function fetchThirteenFXml(httpClient, cik, accessionNumber, primaryDocument) {
  const cikNoPad = String(parseInt(cik, 10));
  const accNoDash = accessionNumber.replace(/-/g, '');
  const baseUrl = `https://www.sec.gov/Archives/edgar/data/${cikNoPad}/${accNoDash}`;

  // Try to discover the real infoTable via the filing directory index.
  const indexUrl = `${baseUrl}/index.json`;
  let infoTableFile = null;
  try {
    const indexRes = await httpClient.fetch(indexUrl);
    if (indexRes.ok) {
      const idx = await indexRes.json();
      const items = idx?.directory?.item ?? [];
      // Pick the largest .xml file. Cover page is small; infoTable is big.
      const xmlFiles = items.filter(i => i.name?.endsWith('.xml') && i.size > 0);
      if (xmlFiles.length > 0) {
        xmlFiles.sort((a, b) => b.size - a.size);
        infoTableFile = xmlFiles[0].name;
      }
    }
  } catch {
    // index.json unavailable (older filings, network blip) — fall through to fallback.
  }

  const fileName = infoTableFile ?? primaryDocument;
  const fallbackRes = await httpClient.fetch(`${baseUrl}/${fileName}`);
  if (!fallbackRes.ok) throw new Error(`13F XML HTTP ${fallbackRes.status} for ${fileName}`);
  return fallbackRes.text();
}
