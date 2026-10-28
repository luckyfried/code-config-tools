// The split-flap modules and the one clock that turns them. A module's drum holds the letters in a fixed order, so a
// change spins forward through the alphabet and lands; every module on the page steps on the same frame callback.

// Letters sit last on the drum, so a module spinning to a letter or a blank shows letters on its way there; the ellipsis
// sits before "#", a letter the board seldom lands on, so no module passes through it on the way to a degree sign.
export const DRUM = " 0123456789.,:;!?'\"-+/&%$…#@()°ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const SPOT = new Map([...DRUM].map((letter, index) => [letter, index]));

// The turn timings are --spin-ms and --land-ms in the stylesheet, so the CSS turns and this clock agree.
const timing = (name, fallback) => {
  const value = parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name));
  return value > 0 ? value : fallback;
};
export const SPIN_MS = timing("--spin-ms", 80);
export const LAND_MS = timing("--land-ms", 300);

const MODULE = document.createElement("span");
MODULE.className = "t";
MODULE.innerHTML =
  '<span class="h u"><b> </b></span><span class="h l"><b> </b><i></i></span>' +
  '<span class="f"><span class="h u"><b> </b></span><span class="h k"><b> </b></span></span>';

export class Tile {
  constructor(kind = "") {
    this.el = MODULE.cloneNode(true);
    this.kind = kind;
    this.base = kind ? `t ${kind}` : "t";
    this.el.className = this.base;
    const glyphs = this.el.getElementsByTagName("b");
    this.upper = glyphs[0].firstChild;
    this.lower = glyphs[1].firstChild;
    this.front = glyphs[2].firstChild;
    this.back = glyphs[3].firstChild;
    this.letter = " ";
    this.tone = 0;
    this.queue = [];
    this.nextTone = 0;
    this.at = 0;
    this.set = 0;
    this.spinning = false;
    this.toneShown = 0;
  }

  paint(tone) {
    return tone ? `${this.base} tone-${tone}` : this.base;
  }

  // Shows a letter at once, with no turn: used on a resize and in reduced motion.
  snap(letter, tone = 0) {
    this.letter = letter;
    this.queue.length = 0;
    this.tone = tone;
    this.nextTone = tone;
    write(this.upper, letter);
    write(this.lower, letter);
    this.spinning = false;
    this.el.className = this.paint(tone);
  }

  // One turn from `from` to `to`; `last` is the landing. With `light`, a spin changes the letter in place and only the
  // landing swings the leaf in 3D.
  turn(from, to, last, light) {
    if (!last && light) {
      write(this.upper, to);
      write(this.lower, to);
      if (this.toneShown !== this.tone) this.el.className = this.paint(this.tone);
      this.toneShown = this.tone;
      return;
    }
    write(this.upper, to);
    write(this.lower, from);
    write(this.front, from);
    write(this.back, to);
    // A run of spins is one looping animation the letters change under; the landing turn is its own animation.
    if (last) {
      this.set ^= 1;
      this.el.className = this.paint(this.tone) + (this.set ? " y" : " z");
      this.spinning = false;
    } else if (!this.spinning || this.toneShown !== this.tone) {
      this.el.className = `${this.paint(this.tone)} r`;
      this.spinning = true;
    }
    this.toneShown = this.tone;
  }

  // The landing is over: the module shows its letter at rest.
  rest() {
    write(this.lower, this.letter);
    this.el.className = this.paint(this.tone);
    this.spinning = false;
  }
}

function write(node, letter) {
  if (node.data !== letter) node.data = letter;
}

export function fit(letter) {
  return SPOT.has(letter) ? letter : " ";
}

// The letters a drum shows on its way from `from` to `to`, at most `spins` of them, ending on `to`. With `force`, a
// module already showing `to` goes once round its drum and lands on it again.
function route(from, to, spins, force) {
  const size = DRUM.length;
  const start = SPOT.get(from) ?? 0;
  let distance = ((SPOT.get(to) ?? 0) - start + size) % size;
  if (distance === 0) {
    if (!force) return [];
    distance = size;
  }
  const count = Math.max(1, Math.min(distance, spins));
  const path = [];
  for (let step = distance - count + 1; step <= distance; step += 1) path.push(DRUM[(start + step) % size]);
  return path;
}

export class Flaps {
  constructor({ onTurn = () => {}, light = false } = {}) {
    this.moving = new Set();
    this.onTurn = onTurn;
    this.still = false;
    // On a phone the drum's spins change the letter in place and only the landing turn swings the leaf in 3D.
    this.light = light;
  }

  // Sends `tile` to `letter`, starting at the clock time `at`.
  send(tile, letter, { at = 0, spins = 6, force = false, tone = 0 } = {}) {
    letter = fit(letter);
    if (this.still) {
      tile.snap(letter, tone);
      return;
    }
    const from = tile.queue.length ? tile.queue[tile.queue.length - 1] : tile.letter;
    const path = route(from, letter, spins, force || tone !== tile.tone);
    if (!path.length) return;
    if (tile.queue.length) {
      tile.queue.push(...path);
    } else {
      tile.queue = path;
      if (!this.moving.has(tile)) tile.at = at;
    }
    tile.nextTone = tone;
    this.moving.add(tile);
  }

  // One frame of the board's clock: every module whose time has come takes its next turn or comes to rest.
  frame(now) {
    let turned = 0;
    let landed = 0;
    for (const tile of this.moving) {
      if (now < tile.at) continue;
      if (tile.queue.length === 0) {
        tile.rest();
        this.moving.delete(tile);
        continue;
      }
      // A module that fell behind (a slow frame) skips ahead so the row stays in step with the clock.
      while (tile.queue.length > 1 && now - tile.at > SPIN_MS) {
        tile.letter = tile.queue.shift();
        tile.at += SPIN_MS;
      }
      const from = tile.letter;
      const to = tile.queue.shift();
      const last = tile.queue.length === 0;
      // A landing already a whole landing late would be over by the clock: the module comes to rest on its letter.
      if (last && now - tile.at > LAND_MS) {
        tile.snap(to, tile.nextTone);
        this.moving.delete(tile);
        turned += 1;
        landed += 1;
        continue;
      }
      if (tile.tone !== tile.nextTone) tile.tone = tile.nextTone;
      tile.turn(from, to, last, this.light, now);
      tile.letter = to;
      tile.at = now + (last ? LAND_MS : SPIN_MS);
      turned += 1;
      if (last) landed += 1;
    }
    if (turned) this.onTurn(turned, landed);
    return this.moving.size > 0;
  }
}
