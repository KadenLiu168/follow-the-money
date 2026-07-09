import { fetchLatest13FFilings } from '../edgar/fetch-submissions.js';
import { fetchThirteenFXml } from '../edgar/fetch-thirteen-f-xml.js';
import { parseThirteenF } from '../parsers/thirteen-f.js';
import { compute13FSummary } from '../compute/thirteen-f-summary.js';
import { readFeedJson, writeFeedJson, merge13FFiling } from '../store/feed-json.js';
import { readStateJson, writeStateJson } from '../store/state-json.js';

export async function runPipelineA({ httpClient, config, feedPath, statePath }) {
  const state = readStateJson(statePath);
  let feed = readFeedJson(feedPath);
  let addedCount = 0;
  const errors = [];

  for (const filer of config.thirteenF) {
    try {
      const filings = await fetchLatest13FFilings(httpClient, filer.cik);
      // Process oldest first so each new period can diff against the prior
      // one already in the feed. (fetchLatest13FFilings returns DESC.)
      filings.sort((a, b) => a.filingDate.localeCompare(b.filingDate));
      for (const f of filings) {
        if (state.seenFilings[f.accessionNumber]) continue;
        const xml = await fetchThirteenFXml(
          httpClient,
          filer.cik,
          f.accessionNumber,
          f.primaryDocument,
        );
        const holdings = parseThirteenF(xml);
        const priorFeedEntry = feed.thirteenF.find(
          (e) =>
            e.filerCik === filer.cik.padStart(10, '0') && e.periodOfReport !== f.periodOfReport,
        );
        const summary = compute13FSummary(holdings, priorFeedEntry?.holdings ?? []);
        const entry = {
          filerCik: filer.cik.padStart(10, '0'),
          filerName: filer.name,
          latestFilingDate: f.filingDate,
          latestFormType: f.formType,
          latestAccessionNumber: f.accessionNumber,
          periodOfReport: f.periodOfReport,
          history: [
            { filingDate: f.filingDate, formType: f.formType, accessionNumber: f.accessionNumber },
          ],
          holdings,
          summary,
        };
        // Accumulate in memory via the pure merge (stamps valueUnit, merges history,
        // recomputes stats). The feed is written to disk exactly once after the loop,
        // not once per filing.
        feed = merge13FFiling(feed, entry);
        state.seenFilings[f.accessionNumber] = Date.now();
        addedCount++;
      }
    } catch (err) {
      console.error(`[pipeline-a] ${filer.cik} (${filer.name}): ${err.message}`);
      errors.push({ cik: filer.cik, name: filer.name, error: err.message });
    }
  }
  // Single disk write for the whole run (O(1) instead of once per filing).
  writeFeedJson(feedPath, feed);
  state.lastUpdated = new Date().toISOString();
  writeStateJson(statePath, state);
  return { added: addedCount, errors };
}
