// Every sound is made here with Web Audio: wind that thins out at night, footsteps that change with the ground,
// a chime that climbs a pentatonic scale with each crystal, crickets after dusk, and the jump and landing.
// The context starts on the first press of Start, and the mute choice is remembered.

const MUTE_KEY = "tiny-planet:muted";
const PENTATONIC = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36];

export function createAudio() {
  let ctx = null;
  let master = null;
  let noise = null;
  let wind = null;
  let windFilter = null;
  let cricketTimer = 0;
  let muted = localStorage.getItem(MUTE_KEY) === "1";

  function noiseBuffer() {
    const length = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let b = 0;
    for (let i = 0; i < length; i++) {
      const white = Math.random() * 2 - 1;
      b = 0.97 * b + 0.03 * white;
      data[i] = white * 0.6 + b * 2.2;
    }
    return buffer;
  }

  function start() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return;
    ctx = new Context();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.8;
    const comp = ctx.createDynamicsCompressor();
    master.connect(comp).connect(ctx.destination);
    noise = noiseBuffer();

    const source = ctx.createBufferSource();
    source.buffer = noise;
    source.loop = true;
    windFilter = ctx.createBiquadFilter();
    windFilter.type = "bandpass";
    windFilter.frequency.value = 520;
    windFilter.Q.value = 0.7;
    wind = ctx.createGain();
    wind.gain.value = 0.05;
    source.connect(windFilter).connect(wind).connect(master);
    source.start();
  }

  function burst({ type = "bandpass", frequency, q = 1, gain, attack = 0.004, decay, when = 0 }) {
    const t = ctx.currentTime + when;
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const f = ctx.createBiquadFilter();
    f.type = type;
    f.frequency.value = frequency;
    f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    src.connect(f).connect(g).connect(master);
    src.start(t, Math.random() * 1.5);
    src.stop(t + attack + decay + 0.05);
  }

  function tone({ frequency, to, type = "sine", gain, attack = 0.005, decay, when = 0 }) {
    const t = ctx.currentTime + when;
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(frequency, t);
    if (to) o.frequency.exponentialRampToValueAtTime(to, t + attack + decay * 0.6);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    o.connect(g).connect(master);
    o.start(t);
    o.stop(t + attack + decay + 0.05);
  }

  const live = () => ctx && !muted && ctx.state === "running";

  return {
    start,
    get muted() {
      return muted;
    },
    setMuted(on) {
      muted = on;
      localStorage.setItem(MUTE_KEY, on ? "1" : "0");
      if (master) master.gain.setTargetAtTime(on ? 0 : 0.8, ctx.currentTime, 0.05);
    },
    pause(on) {
      if (!ctx) return;
      if (on) ctx.suspend();
      else ctx.resume();
    },
    step(surface, run) {
      if (!live()) return;
      const loud = run ? 1.25 : 1;
      if (surface === "water") {
        burst({ frequency: 700 + Math.random() * 300, q: 0.9, gain: 0.22 * loud, decay: 0.22 });
        burst({ type: "highpass", frequency: 3200, gain: 0.05 * loud, decay: 0.12, when: 0.03 });
      } else if (surface === "rock") {
        burst({ type: "highpass", frequency: 2600, gain: 0.1 * loud, attack: 0.002, decay: 0.05 });
        tone({ frequency: 140, to: 90, gain: 0.08 * loud, decay: 0.07 });
      } else if (surface === "snow") {
        burst({ type: "lowpass", frequency: 1500, gain: 0.2 * loud, attack: 0.01, decay: 0.12 });
      } else if (surface === "sand") {
        burst({ frequency: 1300, q: 0.6, gain: 0.12 * loud, attack: 0.01, decay: 0.09 });
      } else {
        burst({ frequency: 1900 + Math.random() * 500, q: 0.8, gain: 0.1 * loud, attack: 0.006, decay: 0.07 });
      }
    },
    jump() {
      if (!live()) return;
      tone({ frequency: 330, to: 620, type: "triangle", gain: 0.1, decay: 0.16 });
    },
    land(impact) {
      if (!live()) return;
      const k = Math.min(1, impact / 9);
      burst({ type: "lowpass", frequency: 500, gain: 0.25 * k + 0.05, attack: 0.003, decay: 0.16 });
    },
    chime(index) {
      if (!live()) return;
      const base = 523.25;
      const n = PENTATONIC[Math.min(index, PENTATONIC.length - 1)];
      const f = base * Math.pow(2, n / 12);
      tone({ frequency: f, type: "sine", gain: 0.28, decay: 1.4 });
      tone({ frequency: f * 2, type: "sine", gain: 0.08, decay: 0.9, when: 0.02 });
      tone({ frequency: f * 1.5, type: "triangle", gain: 0.06, decay: 0.7, when: 0.09 });
      burst({ type: "highpass", frequency: 6000, gain: 0.05, decay: 0.4 });
    },
    win() {
      if (!live()) return;
      [0, 4, 7, 12, 16].forEach((n, i) => {
        tone({ frequency: 523.25 * Math.pow(2, n / 12), gain: 0.18, decay: 1.6, when: i * 0.11 });
      });
    },
    nightfall() {
      if (!live()) return;
      [12, 7, 4, 0].forEach((n, i) => {
        tone({ frequency: 392 * Math.pow(2, n / 12), type: "triangle", gain: 0.12, decay: 1.4, when: i * 0.2 });
      });
    },
    // night runs 0 at day to 1 at full night.
    update(dt, night, active) {
      if (!ctx) return;
      const t = ctx.currentTime;
      wind.gain.setTargetAtTime(active ? 0.05 * (1 - night * 0.6) : 0.025, t, 0.5);
      windFilter.frequency.setTargetAtTime(520 - night * 260, t, 0.5);
      if (!live() || night < 0.3 || !active) return;
      cricketTimer -= dt;
      if (cricketTimer < 0) {
        cricketTimer = 0.5 + Math.random() * 1.3;
        const f = 4200 + Math.random() * 500;
        for (let i = 0; i < 3; i++) {
          tone({ frequency: f, type: "sine", gain: 0.025 * night, attack: 0.003, decay: 0.03, when: i * 0.055 });
        }
      }
    },
  };
}
