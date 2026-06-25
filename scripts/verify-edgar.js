import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

export function loadConfig() {
  return JSON.parse(readFileSync(join(__dirname, '..', 'config', 'default-sources.json'), 'utf8'));
}

export const bucket = { tokens: 10, lastRefill: Date.now(), rate: 10 };
export async function take() {
  while (true) {
    const now = Date.now();
    const elapsed = (now - bucket.lastRefill) / 1000;
    bucket.tokens = Math.min(10, bucket.tokens + elapsed * bucket.rate);
    bucket.lastRefill = now;
    if (bucket.tokens >= 1) { bucket.tokens -= 1; return; }
    await new Promise(r => setTimeout(r, 50));
  }
}

export async function fetchWithRetry(url, ua) {
  await take();
  for (let attempt = 0; attempt < 3; attempt++) {
    const res = await fetch(url, { headers: { 'User-Agent': ua, 'Accept-Encoding': 'gzip, deflate' } });
    if (res.status === 429) {
      const wait = Number(res.headers.get('Retry-After') || 1) * 1000;
      await new Promise(r => setTimeout(r, wait));
      continue;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return res;
  }
  throw new Error(`Failed after 3 retries: ${url}`);
}

export async function checkCik(cik, ua) {
  const url = `https://data.sec.gov/submissions/CIK${cik}.json`;
  const res = await fetchWithRetry(url, ua);
  const data = await res.json();
  return { cik, name: data.name, ok: true };
}

export async function check13DGSearch(ua) {
  const url = `https://efts.sec.gov/LATEST/search-index?q=%22SC+13D%22&dateRange=custom&startDate=2026-06-22&endDate=2026-06-25&forms=SC+13D`;
  const res = await fetchWithRetry(url, ua);
  const data = await res.json();
  return { ok: (data?.hits?.total?.value ?? 0) > 0, count: data?.hits?.total?.value ?? 0 };
}

export async function runVerify(ua) {
  const cfg = loadConfig();
  console.log('Verifying 8 CIKs against EDGAR...');
  const results = [];
  for (const f of cfg.thirteenF) {
    try {
      const r = await checkCik(f.cik, ua);
      results.push(r);
      console.log(`  ✓ ${f.cik} ${r.name}`);
    } catch (e) {
      results.push({ cik: f.cik, ok: false, error: e.message });
      console.log(`  ✗ ${f.cik} ERROR: ${e.message}`);
    }
  }
  const search = await check13DGSearch(ua);
  console.log(`  ${search.ok ? '✓' : '✗'} 13D/G search returned ${search.count} results`);
  const allOk = results.every(r => r.ok) && search.ok;
  console.log(allOk ? '\nVERIFICATION PASSED' : '\nVERIFICATION FAILED');
  return { results, search, allOk };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const UA = process.env.SEC_EDGAR_USER_AGENT;
  if (!UA) {
    console.error('ERROR: SEC_EDGAR_USER_AGENT env var required (format: "AppName email@example.com")');
    process.exit(1);
  }
  runVerify(UA).then(r => process.exit(r.allOk ? 0 : 1)).catch(err => {
    console.error('Fatal:', err);
    process.exit(1);
  });
}