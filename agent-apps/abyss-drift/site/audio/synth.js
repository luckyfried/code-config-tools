// The dive's sound. Every sound was rendered offline to a WAV file in this folder (scripts/make_sounds.py); this
// module plays them and keys their gain and rate to the dive: the motor to thrust, the creak to depth, the sonar
// to the nearest creature not yet photographed, the heartbeat to the held breath.

const FILES = ["motor", "ambience", "creak", "ping", "shutter", "whale", "alarm", "chime", "heartbeat", "blow"];

export function createSynth() {
  let ctx = null;
  let master = null;
  const buffers = {};
  const loops = {};
  let muted = false;
  let loading = null;
  let creakIn = 6;
  let pingIn = 2;
  let alarmIn = 0;
  let whaleIn = 0;

  function unlock() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return loading;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return Promise.resolve();
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.9;
    master.connect(ctx.destination);
    loading = Promise.all(
      FILES.map(async (name) => {
        try {
          const res = await fetch(`./audio/${name}.wav`);
          buffers[name] = await ctx.decodeAudioData(await res.arrayBuffer());
        } catch {
          // A sound that fails to load stays silent; the dive goes on.
        }
      }),
    );
    return loading;
  }

  function play(name, { gain = 1, rate = 1, delay = 0 } = {}) {
    if (!ctx || !buffers[name]) return null;
    const src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = gain;
    src.connect(g).connect(master);
    src.start(ctx.currentTime + delay);
    return src;
  }

  function loop(name, gain) {
    if (!ctx || !buffers[name] || loops[name]) return;
    const src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.loop = true;
    const g = ctx.createGain();
    g.gain.value = 0;
    g.gain.setTargetAtTime(gain, ctx.currentTime, 0.4);
    src.connect(g).connect(master);
    src.start();
    loops[name] = { src, g };
  }

  function setLoop(name, gain, rate) {
    const l = loops[name];
    if (!l) return;
    l.g.gain.setTargetAtTime(gain, ctx.currentTime, 0.15);
    if (rate) l.src.playbackRate.setTargetAtTime(rate, ctx.currentTime, 0.2);
  }

  function stopLoops() {
    for (const [name, l] of Object.entries(loops)) {
      l.g.gain.setTargetAtTime(0, ctx.currentTime, 0.3);
      l.src.stop(ctx.currentTime + 1.5);
      delete loops[name];
    }
  }

  return {
    unlock,
    play,
    get ready() {
      return !!ctx;
    },
    setMuted(m) {
      muted = m;
      if (master) master.gain.setTargetAtTime(m ? 0 : 0.9, ctx.currentTime, 0.05);
    },
    async startDive() {
      await unlock();
      loop("motor", 0.22);
      loop("ambience", 0.5);
      loop("heartbeat", 0);
      creakIn = 5;
      pingIn = 2;
      whaleIn = 0;
    },
    endDive() {
      if (ctx) stopLoops();
    },
    /** s: { dt, thrust, descend, depth, nearest (meters or Infinity), airLow, breath, whaleNear, paused } */
    update(s) {
      if (!ctx || !loops.motor) return;
      if (s.paused) {
        setLoop("motor", 0);
        setLoop("ambience", 0.15);
        setLoop("heartbeat", 0);
        return;
      }
      const work = Math.min(1, Math.abs(s.thrust) + s.descend * 0.8);
      setLoop("motor", (0.14 + work * 0.2) * (1 - s.breath * 0.8), 0.85 + work * 0.45);
      setLoop("ambience", 0.35 + Math.min(0.4, s.depth / 900), 1 - Math.min(0.25, s.depth / 2400));
      setLoop("heartbeat", s.breath * 0.7, 1);
      creakIn -= s.dt;
      if (creakIn <= 0) {
        const p = Math.min(1, s.depth / 600);
        if (s.depth > 35) play("creak", { gain: 0.25 + p * 0.55, rate: 1.15 - p * 0.4 });
        creakIn = 9 - p * 5 + Math.random() * 4;
      }
      if (Number.isFinite(s.nearest) && s.nearest < 70 && s.breath < 0.2) {
        pingIn -= s.dt;
        if (pingIn <= 0) {
          play("ping", { gain: 0.3, rate: 1 + (1 - s.nearest / 70) * 0.12 });
          pingIn = 0.55 + (s.nearest / 70) * 2.8;
        }
      }
      if (s.airLow) {
        alarmIn -= s.dt;
        if (alarmIn <= 0) {
          play("alarm", { gain: 0.35 });
          alarmIn = 2.2;
        }
      }
      whaleIn -= s.dt;
      if (s.whaleNear && whaleIn <= 0) {
        play("whale", { gain: 0.6, rate: 0.9 + Math.random() * 0.2 });
        whaleIn = 14 + Math.random() * 6;
      }
    },
  };
}
