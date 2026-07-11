const VALID_FORMS = new Set(['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A']);

export async function fetchThirteenDGSearch(httpClient, { startDate, endDate, formType }) {
  if (!VALID_FORMS.has(formType)) throw new Error(`invalid formType: ${formType}`);
  const formParam = encodeURIComponent(formType).replace(/%20/g, '+');
  // EDGAR `search-index` IGNORES `startDate`/`endDate` (use `startdt`/`enddt`), and the `forms=`
  // facet returns 0 hits for 2025+ filings. Use the `q=` full-text query with dashed ISO dates.
  // See OpenSpec change fix-edgar-13dg-query (audit F-02 spike, 2026-07-11).
  const url = `https://efts.sec.gov/LATEST/search-index?q=%22${formParam}%22&dateRange=custom&startdt=${startDate}&enddt=${endDate}`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`EDGAR search HTTP ${res.status}`);
  const data = await res.json();
  const hits = data?.hits?.hits ?? [];
  // `q=` text matching is noisy (e.g. "SC TO-T"). Keep only hits whose root_forms is the target
  // form or its "SCHEDULE" alias; drop everything else before it reaches the ingest pipeline.
  return hits.filter((h) => {
    const roots = h?._source?.root_forms ?? [];
    return roots.some((rf) => rf === formType || rf === `SCHEDULE ${formType.slice(3)}`);
  });
}
