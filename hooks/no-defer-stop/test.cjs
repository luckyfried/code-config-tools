#!/usr/bin/env node
/**
 * Fixture test for no-defer-stop.cjs. Each case writes a scratch transcript,
 * runs the hook as Claude Code does (stdin JSON, stdout decision), and checks
 * whether it blocked. Run: node hooks/no-defer-stop/test.cjs
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const SCRIPT = path.join(__dirname, 'no-defer-stop.cjs');
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'no-defer-stop-test-'));

function userEntry(uuid, text) {
  return { type: 'user', uuid, message: { role: 'user', content: text } };
}

function toolResultEntry(uuid) {
  return {
    type: 'user',
    uuid,
    message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: 't1', content: 'ok' }] },
  };
}

function assistantEntry(text) {
  return { type: 'assistant', uuid: `a-${Math.random()}`, message: { role: 'assistant', content: [{ type: 'text', text }] } };
}

function writeTranscript(name, entries) {
  const file = path.join(scratch, `${name}.jsonl`);
  fs.writeFileSync(file, entries.map(e => JSON.stringify(e)).join('\n') + '\n');
  return file;
}

function runHook(transcriptPath, sessionId, stopHookActive) {
  const input = JSON.stringify({
    session_id: sessionId,
    transcript_path: transcriptPath,
    stop_hook_active: stopHookActive,
    hook_event_name: 'Stop',
  });
  const result = spawnSync(process.execPath, [SCRIPT], { input, encoding: 'utf8' });
  if (result.status !== 0) return { error: `exit ${result.status}: ${result.stderr}` };
  if (!result.stdout.trim()) return { decision: 'allow' };
  const out = JSON.parse(result.stdout);
  return { decision: out.decision, reason: out.reason };
}

const failures = [];
let passed = 0;

function expect(name, got, want) {
  if (got.error || got.decision !== want) {
    failures.push(`${name}: want ${want}, got ${got.error || got.decision}${got.reason ? ` (${got.reason})` : ''}`);
  } else {
    passed += 1;
  }
}

function single(name, text, want) {
  const transcript = writeTranscript(name, [userEntry(`u-${name}`, 'do the work'), assistantEntry(text)]);
  expect(name, runHook(transcript, `s-${name}`, false), want);
}

single('in-progress-blocks', 'Working on it.\n\nSTATUS: IN_PROGRESS\nSCOPE: the fix\nCONFIDENCE: MED', 'block');
single('scoping-blocks', 'STATUS: SCOPING\nSCOPE: read the request', 'block');
single('blocked-allows', 'I need the API key.\n\nSTATUS: BLOCKED\nSCOPE: deploy\nCONFIDENCE: HIGH', 'allow');
single('blocked-with-deferral-text-allows', 'STATUS: BLOCKED\n3 of 5 tests fixed; the rest need your key.', 'allow');
single('done-3-of-5-blocks', 'STATUS: DONE\n3 of 5 tests fixed.', 'block');
single('done-5-of-5-allows', 'STATUS: DONE\n5 of 5 tests fixed.', 'allow');
single('done-nothing-deferred-allows', 'STATUS: DONE\nNothing was deferred.', 'allow');
single('done-no-items-skipped-allows', 'STATUS: DONE\nNo items were skipped.', 'allow');
single('done-out-of-scope-allows', 'STATUS: DONE\nAll requested work is complete; deployment is out of scope.', 'allow');
single('done-2-remaining-blocks', 'STATUS: DONE\nFinished two items (2 remaining).', 'block');
single('done-0-remaining-allows', 'STATUS: DONE\nFinished every item (0 remaining).', 'allow');
single('done-follow-up-pr-blocks', 'STATUS: DONE\nThe docs change goes in a follow-up PR.', 'block');
single('done-not-in-a-follow-up-allows', 'STATUS: DONE\nEverything landed here, not in a follow-up.', 'allow');
single('nice-to-have-blocks', 'Core is done; the cache is a nice-to-have.', 'block');
single('no-status-plain-allows', 'Fixed the parser and its tests pass (exit 0).', 'allow');
single('promise-last-line-blocks', 'STATUS: DONE\nThe parser is fixed.\nI\'ll wire the rest next.', 'block');
single('promise-before-trailing-status-blocks', 'The parser is fixed.\nI will add the tests next.\n\n```\nSTATUS: DONE\nSCOPE: parser\nCONFIDENCE: HIGH\n```', 'block');
single('promise-mid-message-allows', "I'll explain the change.\nThe parser is fixed and tested.", 'allow');
single('let-me-know-blocks', 'The draft is ready.\nLet me know when you want the rest.', 'block');

// The counter: three blocks since the person last spoke, then the stop is allowed.
{
  const name = 'loop-guard';
  const entries = [userEntry('u-loop-1', 'do the work'), assistantEntry('STATUS: IN_PROGRESS')];
  const transcript = writeTranscript(name, entries);
  expect(`${name}-block-1`, runHook(transcript, name, false), 'block');
  entries.push(toolResultEntry('tr-1'), assistantEntry('STATUS: IN_PROGRESS'));
  writeTranscript(name, entries);
  expect(`${name}-block-2-after-tool-result`, runHook(transcript, name, true), 'block');
  expect(`${name}-block-3`, runHook(transcript, name, true), 'block');
  expect(`${name}-fourth-allows`, runHook(transcript, name, true), 'allow');

  // A stop with stop_hook_active false starts the count again.
  expect(`${name}-stop-hook-inactive-resets`, runHook(transcript, name, false), 'block');
  expect(`${name}-after-reset-block-2`, runHook(transcript, name, true), 'block');
}

// Errors allow the stop.
expect('missing-transcript-allows', runHook(path.join(scratch, 'absent.jsonl'), 'absent', false), 'allow');
{
  const result = spawnSync(process.execPath, [SCRIPT], { input: 'not json', encoding: 'utf8' });
  expect('bad-json-allows', result.status === 0 && !result.stdout ? { decision: 'allow' } : { decision: 'other' }, 'allow');
}

fs.rmSync(scratch, { recursive: true, force: true });

if (failures.length > 0) {
  for (const failure of failures) console.error(`FAIL ${failure}`);
  process.exit(1);
}
console.log(`no-defer-stop: ${passed} cases passed`);
