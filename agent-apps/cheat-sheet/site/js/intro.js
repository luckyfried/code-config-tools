// The first visit shows the sheet working on its own: it types a word into the search, the sheet closes up around the
// matches, the top match plays its keys, the search clears and the sheet opens back out, then Learn turns every cap over and one row flips back. Any tap or key press ends it at once.

const wait = (ms, signal) => new Promise((done, fail) => {
  const t = setTimeout(done, ms);
  signal.addEventListener("abort", () => { clearTimeout(t); fail(new Error("stopped")); }, { once: true });
});

// A word from the sheet's own actions that finds two to four rows, preferring one that spans two sections.
export function pickWord(rows) {
  const counts = new Map();
  for (const item of rows) {
    const words = new Set(item.entry.action.toLowerCase().match(/[a-z]{4,}/g) || []);
    for (const w of words) {
      const c = counts.get(w) || { n: 0, sections: new Set() };
      c.n++; c.sections.add(item.section);
      counts.set(w, c);
    }
  }
  const fits = [...counts].filter(([, c]) => c.n >= 2 && c.n <= 4);
  const spread = fits.find(([, c]) => c.sections.size > 1);
  return (spread || fits[0] || [null])[0];
}

export async function playIntro({ word, input, box, filter, setLearning, rows, play, turn, signal }) {
  await wait(3200, signal);
  if (word) {
    box.classList.add("is-demo", "has-query");
    for (let i = 1; i <= word.length; i++) {
      input.value = word.slice(0, i);
      filter(input.value);
      await wait(130, signal);
    }
    await wait(650, signal);
    const top = rows().find((item) => item.visible && item.row.querySelector(".cap"));
    if (top) play(top.row);
    await wait(1100, signal);
    input.value = "";
    filter("");
    box.classList.remove("is-demo", "has-query");
    await wait(1000, signal);
  }
  setLearning(true);
  await wait(1700, signal);
  const pick = rows().find((item) => item.row.querySelectorAll(".cap").length >= 3 && item.visible);
  if (pick) {
    pick.row.classList.add("is-revealed");
    turn(pick.row);
    await wait(1200, signal);
    pick.row.classList.remove("is-revealed");
    turn(pick.row);
    await wait(500, signal);
  }
  setLearning(false);
}
