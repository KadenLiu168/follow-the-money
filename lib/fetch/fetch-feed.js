import { writeFile, rename, mkdir, readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';

const STATIC_FILES = [
  { urlPath: 'feed-13f.json',            localName: 'feed-13f.json' },
  { urlPath: 'state-13f.json',           localName: 'state-13f.json' },
  { urlPath: 'feed-13dg/manifest.json',  localName: 'feed-13dg/manifest.json' },
  { urlPath: 'state-13dg.ndjson',        localName: 'state-13dg.ndjson' },
];

const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_RETRIES = 2;
const RETRY_DELAYS_MS = [500, 1500];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchOne(url, { timeoutMs, retries }) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timer);
      if (!res.ok) {
        lastErr = new Error(`HTTP ${res.status} for ${url}`);
        if (res.status >= 400 && res.status < 500 && res.status !== 408 && res.status !== 429) {
          // Non-retryable client error
          return { ok: false, status: res.status };
        }
      } else {
        const body = await res.text();
        return { ok: true, body };
      }
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
    }
    if (attempt < retries) {
      const delay = RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)];
      await sleep(delay);
    }
  }
  return { ok: false, error: lastErr };
}

async function writeAtomic(targetDir, localName, body) {
  const finalPath = join(targetDir, localName);
  const tmpPath = `${finalPath}.tmp`;
  await mkdir(dirname(finalPath), { recursive: true });
  await writeFile(tmpPath, body, 'utf8');
  await rename(tmpPath, finalPath);
}

export async function fetchFeed({
  repoOwner,
  repoName,
  targetDir,
  branch = 'main',
  httpTimeoutMs = DEFAULT_TIMEOUT_MS,
  retries = DEFAULT_RETRIES,
}) {
  const baseUrl = `https://raw.githubusercontent.com/${repoOwner}/${repoName}/${branch}`;
  const partialFilesWritten = [];

  // Phase 1: fetch all STATIC_FILES in parallel
  const staticResults = await Promise.all(
    STATIC_FILES.map(async ({ urlPath, localName }) => {
      const url = `${baseUrl}/${urlPath}`;
      const r = await fetchOne(url, { timeoutMs: httpTimeoutMs, retries });
      if (!r.ok) return { localName, ok: false, error: r.error || new Error(`HTTP ${r.status}`) };
      try {
        await writeAtomic(targetDir, localName, r.body);
      } catch (err) {
        console.error(`[fetch-feed] static write failed for ${localName}: ${err.message}`);
        return { localName, ok: false, error: err };
      }
      return { localName, ok: true };
    })
  );

  // Collect failures and successes from phase 1
  const staticFailures = staticResults.filter((r) => !r.ok);
  for (const r of staticResults) {
    if (r.ok) partialFilesWritten.push(r.localName);
  }

  // Hard fail if any static file failed
  if (staticFailures.length > 0) {
    const failedNames = staticFailures.map((f) => f.localName).join(', ');
    const firstErr = staticFailures[0].error;
    return {
      ok: false,
      reason: `static_fetch_failed: ${failedNames}: ${firstErr?.message ?? 'unknown'}`,
      filesWritten: [],
      partialFilesWritten,
    };
  }

  // Phase 2: discover NDJSON files from manifest
  const manifestPath = join(targetDir, 'feed-13dg', 'manifest.json');
  let manifest;
  try {
    manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  } catch (err) {
    return {
      ok: false,
      reason: `manifest_unreadable: ${err.message}`,
      filesWritten: [],
      partialFilesWritten,
    };
  }

  const ndjsonFiles = Object.values(manifest.years ?? {}).map((y) => y.file).filter(Boolean);
  const ndjsonResults = await Promise.all(
    ndjsonFiles.map(async (filePath) => {
      const url = `${baseUrl}/${filePath}`;
      const localName = filePath;
      const r = await fetchOne(url, { timeoutMs: httpTimeoutMs, retries });
      if (!r.ok) return { localName, ok: false };
      try {
        await writeAtomic(targetDir, localName, r.body);
      } catch (err) {
        console.warn(`[fetch-feed] NDJSON write failed for ${localName}: ${err.message}`);
        return { localName, ok: false };
      }
      return { localName, ok: true };
    })
  );

  const filesWritten = [
    ...staticResults.filter((r) => r.ok).map((r) => r.localName),
    ...ndjsonResults.filter((r) => r.ok).map((r) => r.localName),
  ];

  const ndjsonFailures = ndjsonResults.filter((r) => !r.ok);
  if (ndjsonFailures.length > 0) {
    // Soft fail — manifest was reachable but some years are missing
    console.warn(`[fetch-feed] missing NDJSON files: ${ndjsonFailures.map((f) => f.localName).join(', ')}`);
  }

  return { ok: true, filesWritten, partialFilesWritten: [] };
}