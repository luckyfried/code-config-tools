// The table's sounds: a glass set-down, a capture, the check chime, and the clock's last-seconds tick. The audio
// context opens on the first tap or key, as browsers require; sounds before that are silent.
const FILES = { move: "set-down", capture: "capture", check: "check", tick: "tick" };

export class Sound {
  constructor(enabled) {
    this.enabled = enabled;
    this.buffers = {};
    this.ctx = null;
    const unlock = () => {
      removeEventListener("pointerdown", unlock);
      removeEventListener("keydown", unlock);
      this.open();
    };
    addEventListener("pointerdown", unlock);
    addEventListener("keydown", unlock);
  }

  async open() {
    if (this.ctx) return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    this.ctx = new Ctx();
    this.gain = this.ctx.createGain();
    this.gain.gain.value = 0.7;
    this.gain.connect(this.ctx.destination);
    await Promise.all(Object.entries(FILES).map(async ([kind, file]) => {
      try {
        const data = await (await fetch(`./sound/${file}.wav`)).arrayBuffer();
        this.buffers[kind] = await this.ctx.decodeAudioData(data);
      } catch { /* a sound that cannot load stays quiet */ }
    }));
  }

  play(kind, volume = 1) {
    if (!this.enabled || !this.ctx || !this.buffers[kind]) return;
    const src = this.ctx.createBufferSource();
    src.buffer = this.buffers[kind];
    src.playbackRate.value = 0.96 + Math.random() * 0.08;
    const g = this.ctx.createGain();
    g.gain.value = volume;
    src.connect(g).connect(this.gain);
    src.start();
  }
}
