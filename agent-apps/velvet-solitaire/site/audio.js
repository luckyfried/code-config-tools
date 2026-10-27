// The table's sounds: four samples rendered ahead of time, played through Web Audio with a
// little pitch and gain variation on every play, so no two drops sound alike.

const FILES = { snap: "./sound/snap.wav", slide: "./sound/slide.wav", flip: "./sound/flip.wav", whoosh: "./sound/whoosh.wav" };

export function createAudio({ enabled = true } = {}) {
  let ctx = null;
  let master = null;
  const buffers = {};
  const raw = {};
  let on = enabled;
  let unlocked = false;
  let lastAt = {};

  // Fetch the files early; decode once a gesture has made an audio context.
  const fetched = Promise.all(
    Object.entries(FILES).map(([name, url]) =>
      fetch(url)
        .then((r) => (r.ok ? r.arrayBuffer() : null))
        .then((data) => {
          raw[name] = data;
        })
        .catch(() => {
          raw[name] = null;
        }),
    ),
  );

  async function unlock() {
    if (unlocked) return;
    unlocked = true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.8;
    master.connect(ctx.destination);
    await fetched;
    await Promise.all(
      Object.entries(raw).map(async ([name, data]) => {
        if (!data) return;
        try {
          buffers[name] = await ctx.decodeAudioData(data.slice(0));
        } catch {
          buffers[name] = null;
        }
      }),
    );
  }

  /** Plays a sound: `pitch` and `gain` vary around 1 unless given. */
  function play(name, { pitch = null, gain = null, delay = 0 } = {}) {
    if (!on || !ctx || !buffers[name]) return;
    if (ctx.state === "suspended") ctx.resume();
    const now = ctx.currentTime;
    // Many cards landing in one frame make one sound, not a burst.
    if (lastAt[name] && now - lastAt[name] < 0.03 && delay === 0) return;
    lastAt[name] = now;
    const src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.playbackRate.value = pitch ?? 0.9 + Math.random() * 0.22;
    const g = ctx.createGain();
    g.gain.value = gain ?? 0.62 + Math.random() * 0.38;
    src.connect(g);
    g.connect(master);
    src.start(now + delay);
  }

  return {
    unlock,
    play,
    set enabled(v) {
      on = !!v;
    },
    get enabled() {
      return on;
    },
  };
}
