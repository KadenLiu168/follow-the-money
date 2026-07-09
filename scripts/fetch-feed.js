import { homedir } from 'node:os';
import { join } from 'node:path';
import { fetchFeed } from '../lib/fetch/fetch-feed.js';

const REPO_OWNER = 'KadenLiu168';
const REPO_NAME = 'follow-the-money';
const BRANCH = 'main';

export function defaultTargetDir() {
  if (process.env.FOLLOW_THE_MONEY_FEED_DIR) return process.env.FOLLOW_THE_MONEY_FEED_DIR;
  const home = homedir();
  if (process.platform === 'darwin')
    return join(home, 'Library', 'Caches', 'follow-the-money', 'feed');
  if (process.platform === 'win32') {
    const local = process.env.LOCALAPPDATA || join(home, 'AppData', 'Local');
    return join(local, 'follow-the-money', 'feed');
  }
  // linux and others
  const xdg = process.env.XDG_CACHE_HOME;
  return xdg
    ? join(xdg, 'follow-the-money', 'feed')
    : join(home, '.cache', 'follow-the-money', 'feed');
}

async function main() {
  const targetDir = defaultTargetDir();
  const result = await fetchFeed({
    repoOwner: REPO_OWNER,
    repoName: REPO_NAME,
    branch: BRANCH,
    targetDir,
  });
  process.stdout.write(JSON.stringify(result) + '\n');
  process.exit(result.ok ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error('[fetch-feed] Fatal:', err);
    process.exit(1);
  });
}

export { main };
