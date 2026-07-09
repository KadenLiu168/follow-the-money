// Canonical EDGAR Archives URL construction, shared by the 13F XML fetcher
// and pipeline-b so the `cikNoPad` / `accNoDash` / `baseUrl` template is
// defined in exactly one place (previously duplicated in both modules).

function cikNoPad(cik) {
  return String(parseInt(cik, 10));
}

function accNoDash(accession) {
  return accession.replace(/-/g, '');
}

export function edgarArchiveUrl(cik, accession) {
  return `https://www.sec.gov/Archives/edgar/data/${cikNoPad(cik)}/${accNoDash(accession)}`;
}

export function edgarDocUrl(cik, accession, fileName) {
  return `${edgarArchiveUrl(cik, accession)}/${fileName}`;
}
