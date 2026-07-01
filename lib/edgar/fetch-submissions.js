const THIRTEEN_F_FORMS = new Set(['13F-HR', '13F-HR/A']);

export async function fetchLatest13FFilings(httpClient, cik) {
  const padded = cik.padStart(10, '0');
  const url = `https://data.sec.gov/submissions/CIK${padded}.json`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`submissions HTTP ${res.status} for CIK ${cik}`);
  const data = await res.json();
  const recent = data.filings?.recent;
  if (!recent) return [];
  const out = [];
  for (let i = 0; i < recent.form.length; i++) {
    const formType = recent.form[i];
    if (!THIRTEEN_F_FORMS.has(formType)) continue;
    // Skip pre-XML-era 13F filings (pre-2003 used .txt primaryDocument).
    const primaryDoc = recent.primaryDocument[i];
    if (!primaryDoc || !primaryDoc.toLowerCase().endsWith('.xml')) continue;
    out.push({
      filingDate: recent.filingDate[i],
      formType,
      accessionNumber: recent.accessionNumber[i],
      primaryDocument: primaryDoc,
      periodOfReport: recent.reportDate[i],
    });
  }
  out.sort((a, b) => b.filingDate.localeCompare(a.filingDate));
  return out;
}