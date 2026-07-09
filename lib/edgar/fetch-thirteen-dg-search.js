const VALID_FORMS = new Set(['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A']);

export async function fetchThirteenDGSearch(httpClient, { startDate, endDate, formType }) {
  if (!VALID_FORMS.has(formType)) throw new Error(`invalid formType: ${formType}`);
  const formParam = encodeURIComponent(formType).replace(/%20/g, '+');
  const url = `https://efts.sec.gov/LATEST/search-index?q=&forms=${formParam}&dateRange=custom&startDate=${startDate}&endDate=${endDate}`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`EDGAR search HTTP ${res.status}`);
  const data = await res.json();
  return data?.hits?.hits ?? [];
}
