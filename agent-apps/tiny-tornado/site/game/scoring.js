// The tally of what the storm lifted, and the damage report's sentence ("twelve cows, three cars, and one barn").
import { KINDS } from "./lift.js";

// The order the report names things in: the funniest first, the fences last.
export const REPORT_ORDER = ["cow", "car", "barn", "house", "truck", "silo", "tree", "hay bale", "fence"];

const ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
  "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"];
const TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"];

export function numberWord(n) {
  if (n < 20) return ONES[n];
  if (n < 100) return TENS[Math.floor(n / 10)] + (n % 10 ? `-${ONES[n % 10]}` : "");
  return String(n);
}

export function listWords(parts) {
  if (parts.length <= 1) return parts.join("");
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

export function createTally() {
  const counts = {};
  return {
    counts,
    add(type) {
      const kind = KINDS[type];
      counts[kind.word] = (counts[kind.word] || 0) + 1;
    },
    clear() {
      for (const k of Object.keys(counts)) delete counts[k];
    },
    total() {
      return Object.values(counts).reduce((a, b) => a + b, 0);
    },
    // "twelve cows, three cars, and one barn", from the first four kinds in REPORT_ORDER the storm lifted.
    sentence(limit = 4) {
      const parts = [];
      for (const word of REPORT_ORDER) {
        const n = counts[word] || 0;
        if (!n) continue;
        const plural = Object.values(KINDS).find((k) => k.word === word).words;
        parts.push(`${numberWord(n)} ${n === 1 ? word : plural}`);
        if (parts.length === limit) break;
      }
      return listWords(parts);
    },
    rows() {
      return REPORT_ORDER.filter((w) => counts[w]).map((word) => {
        const n = counts[word];
        const plural = Object.values(KINDS).find((k) => k.word === word).words;
        return { label: n === 1 ? word : plural, n };
      });
    },
  };
}

export function massText(t) {
  return t < 10 ? t.toFixed(1) : String(Math.round(t));
}
