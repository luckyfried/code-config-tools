// The first visit's welcome: once the books have flown onto the shelf, one favorite tilts out, floats to the
// camera, opens on its note, and goes back. Any touch, click, scroll, or key hands the shelf to the person at once.
const KEY = "reading-shelf:welcomed";

export function shouldWelcome() {
  try {
    return localStorage.getItem(KEY) !== "1";
  } catch {
    return true;
  }
}

function remember() {
  try {
    localStorage.setItem(KEY, "1");
  } catch {
    // Without storage the welcome plays again next visit.
  }
}

export function runWelcome(ctl, bookId, { onEnd }) {
  const timers = [];
  let live = true;
  const at = (ms, fn) => timers.push(setTimeout(() => live && fn(), ms));
  at(560, () => ctl.focus(bookId, { quiet: true }));
  at(1500, () => ctl.open(bookId, { fromWelcome: true }));
  at(6700, () => ctl.close());
  at(8200, () => {
    ctl.focus(null);
    finish(false);
  });
  function finish(interrupted) {
    if (!live) return;
    live = false;
    timers.forEach(clearTimeout);
    remember();
    onEnd(interrupted);
  }
  return { stop: () => finish(true), get live() {
    return live;
  } };
}
