import { fetchLatest13FFilings } from '../edgar/fetch-submissions.js';
import { fetchThirteenFXml } from '../edgar/fetch-thirteen-f-xml.js';
import { parseThirteenF } from '../parsers/thirteen-f.js';
import { compute13FSummary } from '../compute/thirteen-f-summary.js';
import { readFeedJson, upsert13FFiling } from '../store/feed-json.js';
import { readStateJson, writeStateJson } from '../store/state-json.js';

export async function runPipelineA({ httpClient, config, feedPath, statePath }) {
  const state = readStateJson(statePath);
  const feed = readFeedJson(feedPath);
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
        const xml = await fetchThirteenFXml(httpClient, filer.cik, f.accessionNumber, f.primaryDocument);
        const holdings = parseThirteenF(xml);
        const priorFeedEntry = feed.thirteenF.find(e => e.filerCik === filer.cik.padStart(10, '0') && e.periodOfReport !== f.periodOfReport);
        const summary = compute13FSummary(holdings, priorFeedEntry?.holdings ?? []);
        const entry = {
          filerCik: filer.cik.padStart(10, '0'),
          filerName: filer.name,
          latestFilingDate: f.filingDate,
          latestFormType: f.formType,
          latestAccessionNumber: f.accessionNumber,
          periodOfReport: f.periodOfReport,
          history: [{ filingDate: f.filingDate, formType: f.formType, accessionNumber: f.accessionNumber }],
          holdings, summary,
        };
        upsert13FFiling(feedPath, entry);
        // Keep the in-memory feed in sync so subsequent filings in this same run
        // (e.g. Q1 2026 after Q4 2025) can find prior-period holdings for diff.
        const existingIdx = feed.thirteenF.findIndex(e => e.filerCik === entry.filerCik && e.periodOfReport === entry.periodOfReport);
        if (existingIdx >= 0) feed.thirteenF[existingIdx] = { ...entry, history: feed.thirteenF[existingIdx].history };
        else feed.thirteenF.push(entry);
        state.seenFilings[f.accessionNumber] = Date.now();
        addedCount++;
      }
    } catch (err) {
      console.error(`[pipeline-a] ${filer.cik} (${filer.name}): ${err.message}`);
      errors.push({ cik: filer.cik, name: filer.name, error: err.message });
    }
  }
  state.lastUpdated = new Date().toISOString();
  writeStateJson(statePath, state);
  return { added: addedCount, errors };
}