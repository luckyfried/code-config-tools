// The new-game sheet (opponent, side, level, clock, board, sound) and the same sheet as settings mid-game, where
// only the board, the sound, and the turning of the board can change.
const LEVELS = {
  1: "Level 1 plays quickly and makes mistakes. Good for learning the moves.",
  2: "Level 2 sees simple tactics and still leaves openings.",
  3: "Level 3 looks a few moves ahead and punishes loose pieces.",
  4: "Level 4 searches as deep as it can in under two seconds.",
};

export class Setup {
  constructor({ onStart, onSettings, onTryTheme }) {
    this.dialog = document.getElementById("setup");
    this.form = document.getElementById("setup-form");
    this.note = document.getElementById("strength-note");
    this.title = document.getElementById("setup-title");
    this.go = document.getElementById("setup-go");
    this.onStart = onStart;
    this.onSettings = onSettings;
    this.onTryTheme = onTryTheme;
    this.form.addEventListener("change", (e) => {
      this.sync();
      if (e.target.name === "theme") this.onTryTheme(e.target.value);
    });
    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      const values = this.values();
      this.dialog.close();
      if (this.mode === "new") this.onStart(values); else this.onSettings(values);
    });
    document.getElementById("setup-cancel").addEventListener("click", () => this.cancel());
    this.dialog.addEventListener("cancel", (e) => { e.preventDefault(); this.cancel(); });
  }

  setIcons(icons) {
    for (const img of this.form.querySelectorAll("img[data-icon]")) if (icons[img.dataset.icon]) img.src = icons[img.dataset.icon];
  }

  open(mode, settings) {
    this.mode = mode;
    this.before = settings.theme;
    this.form.dataset.mode = mode;
    this.title.textContent = mode === "new" ? "New game" : "Settings";
    this.go.textContent = mode === "new" ? "Start the game" : "Done";
    const f = this.form.elements;
    f.opponent.value = settings.opponent;
    f.human.value = settings.human;
    f.strength.value = String(settings.strength);
    f.clock.value = settings.clock;
    f.theme.value = settings.theme;
    f.sound.checked = settings.sound;
    f.turnBoard.checked = settings.turnBoard;
    this.sync();
    this.dialog.showModal();
  }

  cancel() {
    if (this.form.elements.theme.value !== this.before) this.onTryTheme(this.before);
    this.dialog.close();
  }

  sync() {
    const f = this.form.elements;
    this.form.dataset.opponent = f.opponent.value;
    this.note.textContent = LEVELS[f.strength.value] ?? "";
  }

  values() {
    const f = this.form.elements;
    return {
      opponent: f.opponent.value,
      human: f.human.value,
      strength: Number(f.strength.value),
      clock: f.clock.value,
      theme: f.theme.value,
      sound: f.sound.checked,
      turnBoard: f.turnBoard.checked,
    };
  }
}

// Asks which piece a pawn becomes, with the four glass pieces to choose from.
export function askPromotion(color, icons) {
  const dialog = document.getElementById("promote");
  for (const img of dialog.querySelectorAll("img[data-promo]")) {
    const icon = icons[color + img.dataset.promo];
    if (icon) img.src = icon;
  }
  return new Promise((resolve) => {
    const done = () => {
      dialog.removeEventListener("close", done);
      resolve(dialog.returnValue || null);
    };
    dialog.returnValue = "";
    dialog.addEventListener("close", done);
    dialog.showModal();
  });
}
