// scripts/eval.js
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execSync } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const evalsPath = join(__dirname, '..', 'evals', 'evals.json');
const data = JSON.parse(readFileSync(evalsPath, 'utf8'));

function runChecks(output, checks) {
  const results = [];
  for (const c of checks) {
    let pass = false,
      detail = '';
    try {
      if (c.type === 'contains') pass = output.includes(c.value);
      else if (c.type === 'not_contains') pass = !output.includes(c.value);
      else if (c.type === 'regex') pass = new RegExp(c.pattern, 's').test(output);
      else if (c.type === 'min_length') pass = output.length >= c.value;
      else if (c.type === 'max_length') pass = output.length <= c.value;
      else if (c.type === 'json_field_exists') {
        const j = JSON.parse(output);
        pass = c.field.split('.').reduce((o, k) => o?.[k], j) !== undefined;
      } else if (c.type === 'json_field_equals') {
        const j = JSON.parse(output);
        pass = c.field.split('.').reduce((o, k) => o?.[k], j) === c.value;
      } else if (c.type === 'contains_url_from') {
        pass = output.includes(c.value);
      } else {
        pass = false;
        detail = `unknown check type: ${c.type}`;
      }
    } catch (e) {
      pass = false;
      detail = e.message;
    }
    results.push({ check: c.description, pass, detail });
  }
  return results;
}

// For CI: invoke a deterministic stub that calls the digest script and returns its output.
// Real agent invocation would replace this with the actual agent call.
function invokeAgent(prompt) {
  if (prompt.startsWith('/money')) {
    try {
      return execSync('node scripts/prepare-digest.js', { encoding: 'utf8' });
    } catch {
      return '';
    }
  }
  return '';
}

let totalPass = 0,
  totalFail = 0;
for (const e of data.evals) {
  const out = invokeAgent(e.prompt);
  const results = runChecks(out, e.checks);
  const failed = results.filter((r) => !r.pass);
  const status = failed.length === 0 ? '✓' : '✗';
  console.log(`${status} Eval #${e.id}: ${e.description}`);
  for (const r of results) {
    console.log(`    ${r.pass ? '✓' : '✗'} ${r.check}${r.detail ? ' — ' + r.detail : ''}`);
  }
  if (failed.length === 0) totalPass++;
  else totalFail++;
}
console.log(`\nResult: ${totalPass} passed, ${totalFail} failed`);
process.exit(totalFail === 0 ? 0 : 1);
