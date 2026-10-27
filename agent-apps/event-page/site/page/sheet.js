// The Details sheet on phones: the schedule and the places to stay, over the page.
export function setUpSheet(doc) {
  const sheet = doc.querySelector("[data-sheet]");
  const open = doc.querySelector("[data-open-sheet]");
  if (!sheet || !open) return;
  open.addEventListener("click", () => sheet.showModal());
  doc.querySelector("[data-close-sheet]")?.addEventListener("click", () => sheet.close());
  sheet.addEventListener("click", (e) => { if (e.target === sheet) sheet.close(); });
  sheet.addEventListener("close", () => open.focus());
}
