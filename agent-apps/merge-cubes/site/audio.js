// Plays the sounds rendered into sound/: each merge is the mallet note pitched one step up a pentatonic scale per
// value, so several merges in one swipe climb as a phrase. The context opens on the first touch or key, as browsers
// require; until then the board plays silently.

const FILES = { mallet: "./sound/mallet.wav", thud: "./sound/thud.wav", drop: "./sound/drop.wav", win: "./sound/win.wav" };
// Semitones above C5 for 4, 8, 16, and on: the major pentatonic, climbing an octave every five merges.
const PENTATONIC = [0, 2, 4, 7, 9];

export function createAudio({ enabled = true } = {}) {
  let ctx = null;
  let master = null;
  let on = enabled;
  const buffers = {};
  let loading = null;

  function open() {
    if (ctx || typeof AudioContext === "undefined") return;
    ctx = new AudioContext({ latencyHint: "interactive" });
    master = ctx.createGain();
    master.gain.value = 0.8;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -10;
    comp.ratio.value = 4;
    master.connect(comp).connect(ctx.destination);
    loading = Promise.all(
      Object.entries(FILES).map(async ([name, url]) => {
        try {
          const res = await fetch(url);
          buffers[name] = await ctx.decodeAudioData(await res.arrayBuffer());
        } catch {
          // A sound that cannot load stays quiet; the game plays on.
        }
      }),
    );
  }

  function play(name, { rate = 1, gain = 1, when = 0, pan = 0 } = {}) {
    if (!on || !ctx || !buffers[name]) return;
    if (ctx.state === "suspended") ctx.resume();
    const src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = gain;
    let node = src.connect(g);
    if (pan && ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = Math.max(-1, Math.min(1, pan));
      node = node.connect(p);
    }
    node.connect(master);
    src.start(ctx.currentTime + when);
  }

  function noteRate(value) {
    const step = Math.max(0, Math.round(Math.log2(value)) - 2);
    const semis = PENTATONIC[step % 5] + 12 * Math.floor(step / 5);
    return 2 ** ((semis - 5) / 12);
  }

  return {
    unlock() {
      open();
      if (ctx && ctx.state === "suspended") ctx.resume();
      return loading;
    },
    setEnabled(value) {
      on = value;
    },
    get enabled() {
      return on;
    },
    /** One note per merge, lowest first, a beat apart, so a chain plays as a rising phrase. */
    merges(merges, size) {
      merges.forEach((m, i) => {
        const pan = size > 1 ? (m.c / (size - 1)) * 1.2 - 0.6 : 0;
        play("mallet", { rate: noteRate(m.value), gain: 0.5 + Math.min(0.35, i * 0.06), when: 0.075 + i * 0.06, pan });
      });
    },
    thud() {
      play("thud", { gain: 0.55 });
    },
    drop() {
      play("drop", { gain: 0.22, when: 0.2, rate: 0.96 + Math.random() * 0.08 });
    },
    win() {
      play("win", { gain: 0.8, when: 0.15 });
    },
  };
}
