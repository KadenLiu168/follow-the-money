import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const DEFAULT_LANGUAGE = 'en';

export const USER_CONFIG_PATH = join(homedir(), '.follow-the-money', 'config.json');

// Single safe loader for ~/.follow-the-money/config.json.
// Returns the full parsed config with `language` normalized to DEFAULT_LANGUAGE
// when missing. On any failure (missing file, unreadable, invalid JSON,
// non-object root) returns `{ language: DEFAULT_LANGUAGE }` and never throws —
// matching the unified-loader contract in openspec/specs/config-loading-unified.
export function loadUserConfig() {
  try {
    if (!existsSync(USER_CONFIG_PATH)) return { language: DEFAULT_LANGUAGE };
    const cfg = JSON.parse(readFileSync(USER_CONFIG_PATH, 'utf8'));
    if (cfg === null || typeof cfg !== 'object' || Array.isArray(cfg)) {
      return { language: DEFAULT_LANGUAGE };
    }
    return {
      ...cfg,
      language: typeof cfg.language === 'string' ? cfg.language : DEFAULT_LANGUAGE,
    };
  } catch {
    return { language: DEFAULT_LANGUAGE };
  }
}
