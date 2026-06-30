# EDGAR Fetching

How the aggregator pulls data from SEC EDGAR. Load this when debugging fetch errors, writing parser code, or tuning rate limits.

## Required Secret

`SEC_EDGAR_USER_AGENT` — format `"AppName email@example.com"`

SEC enforces this for all automated access. The aggregator passes it via the `User-Agent` header on every request. Set it in GitHub Actions secrets before the first run; the verify script (`scripts/verify-edgar.js`) will fail without it.

## Endpoints

### 13F — submissions JSON

```
https://data.sec.gov/submissions/CIK<10-digit-cik>.json
```

Returns the filer's recent submissions metadata. The aggregator uses the `filings.recent` block to find new `13F-HR` / `13F-HR/A` accession numbers.

Example:
```
https://data.sec.gov/submissions/CIK0001067983.json
```

### 13F — primary doc XML

```
https://www.sec.gov/Archives/edgar/data/<cik-no-leading-zeros>/<accession-no-dashes>/form13fData.xml
```

Returns the holdings table (CUSIP, shares, value, voting authority). The aggregator parses this into the `holdings` array.

Example:
```
https://www.sec.gov/Archives/edgar/data/1067983/000106798326000456/form13fData.xml
```

### 13D/G — full-text search

```
https://efts.sec.gov/LATEST/search-index?q=%22SC+13D%22&dateRange=custom&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD&forms=SC+13D,SC+13D%2FA,SC+13G,SC+13G%2FA
```

Returns recent filings matching form type within a date range. The aggregator uses this for daily delta scans.

### 13D/G — filing index

```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<cik>&type=SC+13D&dateb=&owner=include&count=40
```

Backup source for 13D/G metadata when search-index results are incomplete.

## Rate Limits

- **Global limit**: 10 requests per second across all EDGAR endpoints
- **Per-second**: enforced — burst > 10 in 1s returns HTTP 429
- **Daily**: SEC publishes a fair-use policy; sustained 10 req/s is the published ceiling

The aggregator implements a **token bucket** (`lib/token-bucket.js`) sized to 10 req/s. All requests go through `lib/http-client.js` which:

1. Acquires a token from the bucket
2. Sends the request with `User-Agent: ${SEC_EDGAR_USER_AGENT}`
3. On HTTP 429: respects `Retry-After` header, waits, retries
4. On 5xx or network error: exponential backoff, max 3 retries
5. On non-retryable 4xx (401, 403, 404): throws — caller decides

## Error Fallbacks

| Failure | Behavior |
|---|---|
| Single CIK 13F fetch fails | Log + skip that CIK, continue with others |
| Single 13F XML parse fails | Skip + log, mark entry as unparsed |
| Single 13D/G search result missing fields | Drop that result, log |
| All CIKs fail | Do not commit feed; let next cron retry |
| Total EDGAR outage | Aggregator exits non-zero; feed unchanged |
| 429 sustained | Token bucket drains, requests wait, eventually succeed |

## Parser Notes

### 13F XML quirks
- `<infoTable>` rows: one per holding
- `CUSIP` may have leading zeros — preserve as string, do not parse to number
- `value` is in thousands of dollars (e.g. `58200000` = $58.2B) — multiply by 1000
- Voting authority split: `Sole` / `Shared` / `None` — sum should equal total shares
- Amendment form (`13F-HR/A`) replaces prior quarter's holdings — see `data-formats.md` merge rule

### 13D/G search quirks
- Search results are paginated; the aggregator uses `from` / `size` parameters
- `accessionNumber` field may be missing in older filings — fall back to filing index
- `issuerTicker` is not always present — leave field empty (not null) when unknown
- Form names appear as `SC 13D`, `SC 13D/A`, `SC 13G`, `SC 13G/A` — match exactly

## Pre-Launch Verification

Before enabling the GitHub Action cron, run `scripts/verify-edgar.js` manually. It validates:

1. All 8 CIKs return 200 from submissions API
2. Sample 13F XML from each CIK parses correctly
3. 13D/G full-text search returns ≥ 1 result for last 3 days
4. At least 3 sample 13D primary docs parse correctly
5. Rate limit handling works (10 req/s sustained)
6. No 429s during normal flow

Output: `VERIFICATION PASSED` or `VERIFICATION FAILED` with detail. Do not enable the cron until this passes.

See `architecture.md` for where the aggregator fits in the data flow.
