// The built-in passages, the word list a weak-keys drill draws from, and the text clean-up every passage gets.

export const PROSE = [
  "The river was quiet that morning, so we took the long way past the mill and counted herons until the fog lifted off the water.",
  "A good habit is small enough to start today. Five minutes at the keyboard, every morning, adds up to a whole week of practice by the end of a season.",
  "She packed a thermos of coffee, two pencils, and a map with the coastline drawn in by hand. The ferry left at seven; the light was already gold.",
  "Keep your wrists loose and your eyes on the line. Speed comes later, after the fingers know where every key lives without being asked.",
  "On Thursday the market sold out of plums by noon, and the baker gave away the last of the rye to anyone who brought their own basket.",
  "Jack quickly boxed up five dozen jars of wax, then zipped the bag shut and walked the long block back to the van parked by the gym.",
  "The old radio hummed in the corner while we sorted the photographs by year: 1964, 1971, and a box marked only with a question mark.",
  "Most mistakes happen at the edges of a word, where one finger hands off to the next. Slow down there and the middle takes care of itself.",
  "We hiked up past the tree line just before dawn, where the wind smelled of snow and the valley below was still a bowl of blue shadow.",
  "Every key has a home and every finger has a lane. Learn the lanes once and the keyboard stops being a map you read and becomes a place you know.",
];

// Accented letters, typed through dead keys or composition on any layout that has them.
export const ACCENTED = [
  "At the café on the corner, Zoë ordered a crème brûlée and a façade of naïve confidence; the waiter, über-polite, said nothing.",
  "Señor Núñez left for São Paulo in the spring, after the fête in Saint-Étienne, with a déjà vu that lasted until the coast.",
];

export const CODE = [
  "function clamp(value, low, high) {\n  return Math.min(high, Math.max(low, value));\n}",
  "const totals = rows\n  .filter((row) => row.done)\n  .reduce((sum, row) => sum + row.minutes, 0);",
  "def mean(values):\n    if not values:\n        return 0.0\n    return sum(values) / len(values)",
  "for (let i = 0; i < keys.length; i += 1) {\n  const rate = errors[i] / (samples[i] || 1);\n  heat[keys[i]] = Math.round(rate * 100);\n}",
  ".card {\n  display: grid;\n  gap: 12px;\n  border-radius: 16px;\n}",
  "if (event.key === \"Escape\") {\n  drill.reset();\n  return;\n}",
  "user = {\"name\": \"Sam\", \"layout\": \"qwerty\", \"days\": [3, 5, 8]}\nprint(f\"{user['name']} typed {sum(user['days'])} drills\")",
  "export async function load(path) {\n  const answer = await fetch(path);\n  return answer.ok ? answer.json() : [];\n}",
];

export const WORDS = (
  "about above across after again against air all almost along also always among and another answer any are area " +
  "around away back bad ball bank base be bear beat became because become bed been before began begin behind being " +
  "below best better between big bird black blue board boat body book both bottom box boy bring brought build built " +
  "busy but buy by call came can car care carry case catch cause center change check child city class clear close " +
  "cold color come common complete could country course cover cross cut dark day deep did different do does dog done " +
  "door down draw dream drive drop dry during each early earth easy eat edge eight else end enough even every example " +
  "eye face fact fall family far farm fast father feel feet few field figure fill find fine fire first fish five fix " +
  "floor fly follow food foot for force form found four free friend from front full game gave get girl give glass go " +
  "gold good got great green ground group grow had half hand happy hard has have he head hear heard heart heavy held " +
  "help her here high hill him his hold home hope horse hot hour house how however huge hundred idea if important in " +
  "inside into is island it its job join jump just keep kept key kind king knew know lake land language large last " +
  "late laugh lay lead learn least leave left less let letter level life light like line list listen little live long " +
  "look lost lot love low machine made main major make man many map mark market may me mean measure meet men might mile " +
  "mind minute miss money month moon more morning most mother mountain move much music must my name near need never new " +
  "next night no north nothing notice now number object of off often oh old on once one only open or order other our " +
  "out over own page paper part pass past pay people perhaps person picture piece place plain plan plane plant play " +
  "please point poor possible power press problem product pull put question quick quickly quiet quite quiz race rain " +
  "ran reach read ready real reason red remember rest rich ride right river road rock room round row rule run said same " +
  "sat save saw say school sea second see seem self sentence set seven several shall shape she ship short should show " +
  "side simple since sing size sky sleep slow small snow so some song soon sound south space speak special speed spell " +
  "spring square stand star start state stay step still stood stop story straight street strong study such summer sun " +
  "sure surface table tail take talk teach tell ten test than that the their them then there these they thing think " +
  "this those though thought three through time to today together told too took top toward town tree true try turn two " +
  "under until up upon us use usual valley very view visit voice vowel wait walk wall want warm was watch water wave way " +
  "we week weight well went were west what wheel when where which while white who whole why wide wild will wind window " +
  "winter wish with without woman wonder wood word work world would write wrote yard year yellow yes yet you young your " +
  "zero zone zoo jazz quartz oxygen box tax wax mix fox six next text exact extra joke jar jacket juice jungle query " +
  "quilt equal squad squeeze zip zigzag puzzle frozen dozen lazy blaze"
).split(" ");

export const CODE_TOKENS = [
  "a[i]", "(x)", "{ }", "x => y", "a !== b", "a && b", "a || b", "i += 1", "n % 2", "x * y", "a - b", "#id", "@media",
  "obj.key", "`${n}`", "'str'", "\"str\"", "x < y", "x > y", "a; b;", "f(a, b)", "[1, 2]", "{ a: 1 }", "x ?? y",
  "path/to", "a_b", "x^2", "$el", "a | b", "a & b", "~x", "!ok", "x = y;", "key: value", "<div>", "</p>",
];

const REPLACE = [
  [/[‘’‚′]/g, "'"],
  [/[“”„″]/g, "\""],
  [/[–—−]/g, "-"],
  [/…/g, "..."],
  [/ /g, " "],
  [/\t/g, "  "],
  [/\r\n?/g, "\n"],
];

/** One passage cleaned for typing: plain quotes and dashes, tabs as two spaces; prose runs as one line of words. */
export function clean(text, mode) {
  let out = String(text || "");
  for (const [pattern, to] of REPLACE) out = out.replace(pattern, to);
  out = out.normalize("NFC");
  if (mode === "code") {
    return out
      .split("\n")
      .map((line) => line.replace(/\s+$/, ""))
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  return out.replace(/\s+/g, " ").trim();
}

/** The passages to use: the person's own when there are any, the built-in set otherwise. */
export function passagesFor(mode, own, layoutHasAccents) {
  const mine = (Array.isArray(own) ? own : []).map((p) => clean(p, mode)).filter(Boolean);
  if (mine.length) return mine;
  if (mode === "code") return CODE.map((p) => clean(p, "code"));
  const set = PROSE.slice();
  if (layoutHasAccents) set.splice(2, 0, ...ACCENTED);
  return set.map((p) => clean(p, "prose"));
}

/** Enough text for a drill of `seconds` at a fast pace, starting at passage `start` and cycling. */
export function drillText(passages, start, seconds, mode) {
  const want = Math.max(240, Math.round((seconds / 60) * 650));
  const join = mode === "code" ? "\n" : " ";
  const parts = [];
  let length = 0;
  for (let n = 0; length < want && n < passages.length * 6; n += 1) {
    const p = passages[(start + n) % passages.length];
    parts.push(p);
    length += p.length + 1;
  }
  return parts.join(join);
}

/** A seeded random source, so a weak-keys drill is the same for the same weak keys on the same day. */
export function seeded(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A drill built from words and code pieces that use the weak characters, weakest weighted most. */
export function weakText(weak, seconds, mode) {
  const chars = weak.map((w) => w.char).filter((c) => c && c.length === 1 && c !== " ");
  if (!chars.length) return null;
  const rand = seeded(chars.join("").split("").reduce((h, c) => h * 31 + c.charCodeAt(0), 7));
  const pool = mode === "code" ? WORDS.concat(CODE_TOKENS) : WORDS;
  const scored = pool
    .map((word) => {
      const lower = word.toLowerCase();
      let score = 0;
      chars.forEach((c, rank) => {
        const hits = lower.split(c).length - 1;
        score += hits * (chars.length - rank);
      });
      return { word, score };
    })
    .filter((w) => w.score > 0)
    .sort((a, b) => b.score - a.score);
  if (!scored.length) return null;
  const top = scored.slice(0, 60);
  const want = Math.max(200, Math.round((seconds / 60) * 520));
  const words = [];
  let length = 0;
  let last = "";
  while (length < want) {
    const pick = top[Math.floor(Math.pow(rand(), 1.6) * top.length)].word;
    if (pick === last && top.length > 1) continue;
    words.push(pick);
    last = pick;
    length += pick.length + 1;
  }
  return words.join(" ");
}
