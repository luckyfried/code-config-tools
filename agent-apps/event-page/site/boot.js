// Marks the page for its opening before the first paint, so the names and the date never show and then vanish.
// The mark lifts on its own after four seconds, so nothing stays hidden if the opening cannot run.
if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
  document.documentElement.classList.add("intro");
  setTimeout(() => document.documentElement.classList.remove("intro"), 4000);
}
