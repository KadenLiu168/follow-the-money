import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

function toKey(name) {
  return name.replace(/\.md$/, '').replace(/-/g, '_');
}

// Attempt the remote tier (GitHub raw). Returns the prompt body on a 2xx
// response, or null on any failure (timeout, network error, non-2xx, or
// `fetch` unavailable). Swallows every error so the caller's top-level await
// can never reject over a network hiccup — we simply fall through to clone.
async function fetchRemoteBody(url) {
  if (typeof fetch !== 'function') return null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// Resolve a single prompt across four outcomes:
//   user > GitHub remote > repo(clone) > missing
async function resolveOne(name, { userDir, repoDir, remoteBaseUrl }) {
  const userPath = join(userDir, name);
  if (existsSync(userPath)) {
    return { source: 'user', text: readFileSync(userPath, 'utf8') };
  }
  const remoteText = await fetchRemoteBody(join(remoteBaseUrl, name));
  if (remoteText !== null) {
    return { source: 'remote', text: remoteText };
  }
  const repoPath = join(repoDir, name);
  if (existsSync(repoPath)) {
    return { source: 'repo', text: readFileSync(repoPath, 'utf8') };
  }
  return { source: 'missing', text: '' };
}

// Resolve prompt files by the single user > remote > repo priority rule.
// Returns a map keyed by file name with `.md` stripped and hyphens →
// underscores (e.g. "format-13f.md" → "format_13f"). `source` ∈
// user | remote | repo | missing. Resolves all names concurrently so one slow
// GitHub fetch adds at most ~5s of wall time, never 5s × N. The result object
// is assembled in `names` order (not resolution order) so the emitted JSON is
// deterministic — JSON.stringify preserves insertion order.
export async function resolvePrompts({ names, userDir, repoDir, remoteBaseUrl }) {
  const resolved = await Promise.all(
    names.map((name) => resolveOne(name, { userDir, repoDir, remoteBaseUrl })),
  );
  const result = {};
  names.forEach((name, i) => {
    result[toKey(name)] = resolved[i];
  });
  return result;
}
