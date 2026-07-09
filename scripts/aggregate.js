import { TokenBucket } from '../lib/token-bucket.js';
import { createHttpClient } from '../lib/http-client.js';
import { runPipelineA } from '../lib/aggregate/pipeline-a.js';
import { runPipelineB } from '../lib/aggregate/pipeline-b.js';
import { loadDefaultSources } from '../lib/config/load-default-sources.js';

const config = loadDefaultSources();

async function main() {
  const UA = process.env.SEC_EDGAR_USER_AGENT;
  if (!UA) {
    console.error('ERROR: SEC_EDGAR_USER_AGENT env var required (format: "AppName email@example.com")');
    process.exit(1);
  }
  const httpClient = createHttpClient({ userAgent: UA, bucket: new TokenBucket(10, 10) });
  const a = await runPipelineA({
    httpClient, config,
    feedPath: 'feed-13f.json', statePath: 'state-13f.json',
  });
  console.log(`[aggregate] Pipeline A: added ${a.added} filings, ${a.errors.length} errors`);

  let b = { added: 0, errors: [] };
  if (config.thirteenDG.enabled) {
    b = await runPipelineB({
      httpClient, config,
      feedDir: 'feed-13dg', statePath: 'state-13dg.ndjson',
      lookbackDays: config.thirteenDG.lookbackDays ?? 3,
    });
    console.log(`[aggregate] Pipeline B: added ${b.added} filings, ${b.errors.length} errors`);
  }

  const totalErrors = (a.errors?.length ?? 0) + (b.errors?.length ?? 0);
  const totalAdded = (a.added ?? 0) + (b.added ?? 0);
  if (totalErrors > 0 && totalAdded === 0) {
    console.error('[aggregate] Total failure: no filings added');
    process.exit(1);
  }
  // Partial success → exit 0 so feed gets committed
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(err => {
    console.error('[aggregate] Fatal:', err);
    process.exit(1);
  });
}

export { main };
