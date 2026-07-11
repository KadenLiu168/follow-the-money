import { TokenBucket } from '../lib/token-bucket.js';
import { createHttpClient } from '../lib/http-client.js';
import { loadDefaultSources } from '../lib/config/load-default-sources.js';
import { DEFAULT_RATE_LIMIT } from '../lib/constants.js';

export function loadConfig() {
  return loadDefaultSources();
}

export async function checkCik(cik, client) {
  const url = `https://data.sec.gov/submissions/CIK${cik}.json`;
  const res = await client.fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  const data = await res.json();
  return { cik, name: data.name, ok: true };
}

export async function check13DGSearch(client) {
  const url = `https://efts.sec.gov/LATEST/search-index?q=%22SC+13D%22&dateRange=custom&startdt=2026-06-22&enddt=2026-06-25`;
  const res = await client.fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  const data = await res.json();
  return { ok: (data?.hits?.total?.value ?? 0) > 0, count: data?.hits?.total?.value ?? 0 };
}

export async function runVerify(ua) {
  // Share the project-standard rate limiter + HTTP client so there is a single
  // throttling/retry implementation across the codebase.
  const bucket = new TokenBucket(DEFAULT_RATE_LIMIT.rate, DEFAULT_RATE_LIMIT.capacity);
  const client = createHttpClient({ userAgent: ua, bucket });
  const cfg = loadConfig();
  console.log('Verifying 8 CIKs against EDGAR...');
  const results = [];
  for (const f of cfg.thirteenF) {
    try {
      const r = await checkCik(f.cik, client);
      results.push(r);
      console.log(`  ✓ ${f.cik} ${r.name}`);
    } catch (e) {
      results.push({ cik: f.cik, ok: false, error: e.message });
      console.log(`  ✗ ${f.cik} ERROR: ${e.message}`);
    }
  }
  const search = await check13DGSearch(client);
  console.log(`  ${search.ok ? '✓' : '✗'} 13D/G search returned ${search.count} results`);
  const allOk = results.every((r) => r.ok) && search.ok;
  console.log(allOk ? '\nVERIFICATION PASSED' : '\nVERIFICATION FAILED');
  return { results, search, allOk };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const UA = process.env.SEC_EDGAR_USER_AGENT;
  if (!UA) {
    console.error(
      'ERROR: SEC_EDGAR_USER_AGENT env var required (format: "AppName email@example.com")',
    );
    process.exit(1);
  }
  runVerify(UA)
    .then((r) => process.exit(r.allOk ? 0 : 1))
    .catch((err) => {
      console.error('Fatal:', err);
      process.exit(1);
    });
}
