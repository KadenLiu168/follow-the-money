export async function fetchThirteenFXml(httpClient, cik, accessionNumber, primaryDocument) {
  const cikNoPad = String(parseInt(cik, 10));
  const accNoDash = accessionNumber.replace(/-/g, '');
  const url = `https://www.sec.gov/Archives/edgar/data/${cikNoPad}/${accNoDash}/${primaryDocument}`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`13F XML HTTP ${res.status} for ${url}`);
  return res.text();
}