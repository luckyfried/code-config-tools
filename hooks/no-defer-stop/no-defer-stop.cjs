#!/usr/bin/env node
/**
 * Stop hook: the agent cannot end a turn with work left over.
 *
 * Reads the last assistant message of the transcript and keys the decision
 * to the status block the Structured Engineering style asks for:
 *
 *   STATUS: IN_PROGRESS | SCOPING  -> block: keep going.
 *   STATUS: BLOCKED                -> allow: the person has to act.
 *   STATUS: DONE, or no status     -> block only on a precise sign of
 *                                     leftover work (a partial count, an
 *                                     explicit deferral phrase, or a last
 *                                     line that promises work not done).
 *
 * A block is `{"decision":"block","reason":"..."}` on stdout with exit 0;
 * an allow prints nothing. After three blocks since the person last spoke the
 * hook allows the stop, so a wedged agent can still return to the person.
 * Every error allows the stop.
 */

const fs = require('fs');
const path = require('path');

const MAX_BLOCKS_SINCE_PERSON_SPOKE = 3;

const STATUS_PATTERN = /^[ \t]*STATUS:[ \t]*([A-Z_]+)\b/m;

// "X of Y <items> <completed>" where X < Y.
const X_OF_Y_PATTERN = /(\d+)\s+of\s+(\d+)\s+(?:checklist\s+)?(?:item|task|check|requirement|step|test|verification|point|thing|issue)s?\s+(?:verified|completed|checked|done|passed|finished|addressed|resolved|fixed|covered|reviewed|confirmed)/gi;

// "(N deferred ...)", "(N skipped)", "(N remaining)" and the like, N > 0.
const N_DEFERRED_PATTERN = /\((\d+)\s+(?:deferred|skipped|remaining|left|omitted|excluded)\b/gi;

const DEFERRAL_PHRASE_PATTERN = new RegExp(
  '\\b(?:' + [
    'left for later',
    'in a follow[- ]up',
    'follow[- ]up PR',
    'next PR',
    'later pass',
    'nice[- ]to[- ]have',
    'deprioritized',
    'deprioritised',
    'will address later',
    'can be addressed later',
  ].join('|') + ')\\b',
  'gi',
);

const NEGATIONS = new Set(['nothing', 'no', 'none', 'not', 'never', 'zero']);
const NEGATION_WINDOW_WORDS = 4;

const PROMISE_PREFIXES = ["I'll ", 'I will ', 'Let me know when', 'Next I will', "Next, I'll", 'Once you '];

const STATUS_BLOCK_LINE = /^[ \t]*(?:STATUS|SCOPE|CONFIDENCE):/;
const FENCE_LINE = /^[ \t]*```/;

function textOf(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content.filter(b => b && b.type === 'text').map(b => b.text).join('\n');
  }
  return '';
}

/** The text of the last assistant message that carries text. */
function lastAssistantText(transcriptPath) {
  const lines = fs.readFileSync(transcriptPath, 'utf8').split('\n');
  let lastText = '';
  for (const line of lines) {
    if (!line.trim()) continue;
    let entry;
    try {
      entry = JSON.parse(line);
    } catch {
      continue;
    }
    const role = entry.message?.role ?? entry.role ?? entry.type;
    const content = entry.message?.content ?? entry.content;
    if (role === 'assistant') {
      const text = textOf(content);
      if (text) lastText = text;
    }
  }
  return lastText;
}

function isNegated(text, index) {
  const before = text.slice(0, index).split(/\s+/).filter(Boolean).slice(-NEGATION_WINDOW_WORDS);
  return before.some(word => NEGATIONS.has(word.toLowerCase().replace(/[^a-z]/g, '')));
}

function deferralFinding(text) {
  for (const match of text.matchAll(X_OF_Y_PATTERN)) {
    const done = parseInt(match[1], 10);
    const total = parseInt(match[2], 10);
    if (done < total && !isNegated(text, match.index)) return match[0];
  }
  for (const match of text.matchAll(N_DEFERRED_PATTERN)) {
    if (parseInt(match[1], 10) > 0 && !isNegated(text, match.index)) return match[0];
  }
  for (const match of text.matchAll(DEFERRAL_PHRASE_PATTERN)) {
    if (!isNegated(text, match.index)) return match[0];
  }
  return null;
}

/** The last non-empty line, read past a trailing status block and its fence. */
function lastLine(text) {
  const lines = text.split('\n');
  while (lines.length > 0) {
    const line = lines[lines.length - 1];
    if (!line.trim() || STATUS_BLOCK_LINE.test(line) || FENCE_LINE.test(line)) {
      lines.pop();
    } else {
      break;
    }
  }
  return lines.length > 0 ? lines[lines.length - 1].trim().replace(/’/g, "'") : '';
}

function blockReason(text) {
  const status = text.match(STATUS_PATTERN)?.[1];
  if (status === 'IN_PROGRESS' || status === 'SCOPING') {
    return `[NO-DEFER HOOK] You reported STATUS: ${status}. Keep going until the work is DONE, or report STATUS: BLOCKED and name the one input only the user can give.`;
  }
  if (status === 'BLOCKED') return null;

  const finding = deferralFinding(text);
  if (finding) {
    return `[NO-DEFER HOOK] The message reports work left undone: "${finding}". Finish it now, or report STATUS: BLOCKED and name the one input only the user can give.`;
  }

  const line = lastLine(text);
  if (PROMISE_PREFIXES.some(prefix => line.startsWith(prefix))) {
    return `[NO-DEFER HOOK] The message ends with a promise of work not done: "${line}". Do that work now.`;
  }
  return null;
}

/**
 * Counts this hook's blocks since the person last spoke in
 * `<transcript dir>/.no-defer-stop/<session id>.json`. `stopHookActive` is
 * the host's `stop_hook_active`: false on the first stop since the person
 * last spoke (the count starts at 0), true on a stop that follows one of our
 * blocks (the file's count holds). Returns false when the count has reached
 * the limit, so the stop is allowed. A counter that cannot be read or written
 * never stops a block.
 */
function takeBlock(transcriptPath, sessionId, stopHookActive) {
  const dir = path.join(path.dirname(transcriptPath), '.no-defer-stop');
  const id = String(sessionId || path.basename(transcriptPath, '.jsonl')).replace(/[^\w.-]/g, '_');
  const file = path.join(dir, `${id}.json`);
  let blocks = 0;
  if (stopHookActive) {
    try {
      const state = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (Number.isInteger(state.blocks)) blocks = state.blocks;
    } catch {
      blocks = 0;
    }
  }
  if (blocks >= MAX_BLOCKS_SINCE_PERSON_SPOKE) return false;
  try {
    fs.mkdirSync(dir, { recursive: true });
    const tmp = `${file}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify({ blocks: blocks + 1 }));
    fs.renameSync(tmp, file);
  } catch {
    // The counter is best effort; the block stands.
  }
  return true;
}

function main(raw) {
  const input = JSON.parse(raw);
  const transcriptPath = input.transcript_path;
  if (!transcriptPath || !fs.existsSync(transcriptPath)) return;
  const reason = blockReason(lastAssistantText(transcriptPath));
  if (!reason) return;
  if (!takeBlock(transcriptPath, input.session_id, input.stop_hook_active === true)) return;
  process.stdout.write(JSON.stringify({ decision: 'block', reason }));
}

let data = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { data += chunk; });
process.stdin.on('end', () => {
  try {
    main(data);
  } catch {
    // Any failure allows the stop.
  }
  process.exit(0);
});
