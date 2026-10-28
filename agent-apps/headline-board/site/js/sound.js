// The clack: a short noise burst through a bandpass, with a low knock under it. The bursts are rendered once with an
// OfflineAudioContext, faster than real time, written out as a WAV file in memory, and played from that file.

const VARIANTS = 6;
const LENGTH = 0.07;

function noise(context, seconds, seed) {
  const buffer = context.createBuffer(1, Math.ceil(seconds * context.sampleRate), context.sampleRate);
  const data = buffer.getChannelData(0);
  let state = seed * 9301 + 49297;
  for (let index = 0; index < data.length; index += 1) {
    state = (state * 9301 + 49297) % 233280;
    data[index] = (state / 233280) * 2 - 1;
  }
  return buffer;
}

async function render(rate) {
  const offline = new OfflineAudioContext(1, Math.ceil(rate * LENGTH * VARIANTS), rate);
  for (let variant = 0; variant < VARIANTS; variant += 1) {
    const at = variant * LENGTH;
    const pitch = 1 + (variant - VARIANTS / 2) * 0.07;

    // The snap of the flap striking the stack.
    const snap = offline.createBufferSource();
    snap.buffer = noise(offline, 0.04, variant + 1);
    const band = offline.createBiquadFilter();
    band.type = "bandpass";
    band.frequency.value = 2600 * pitch;
    band.Q.value = 2.2;
    const snapGain = offline.createGain();
    snapGain.gain.setValueAtTime(0, at);
    snapGain.gain.linearRampToValueAtTime(1, at + 0.0008);
    snapGain.gain.exponentialRampToValueAtTime(0.001, at + 0.022);
    snap.connect(band).connect(snapGain).connect(offline.destination);
    snap.start(at);

    // The knock of the module's body.
    const knock = offline.createBufferSource();
    knock.buffer = noise(offline, 0.05, variant + 11);
    const low = offline.createBiquadFilter();
    low.type = "bandpass";
    low.frequency.value = 520 * pitch;
    low.Q.value = 3.5;
    const knockGain = offline.createGain();
    knockGain.gain.setValueAtTime(0, at);
    knockGain.gain.linearRampToValueAtTime(0.9, at + 0.0015);
    knockGain.gain.exponentialRampToValueAtTime(0.001, at + 0.04);
    knock.connect(low).connect(knockGain).connect(offline.destination);
    knock.start(at);
  }
  return offline.startRendering();
}

function wav(buffer) {
  const samples = buffer.getChannelData(0);
  const bytes = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const text = (offset, value) => [...value].forEach((letter, index) => bytes.setUint8(offset + index, letter.charCodeAt(0)));
  text(0, "RIFF");
  bytes.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  bytes.setUint32(16, 16, true);
  bytes.setUint16(20, 1, true);
  bytes.setUint16(22, 1, true);
  bytes.setUint32(24, buffer.sampleRate, true);
  bytes.setUint32(28, buffer.sampleRate * 2, true);
  bytes.setUint16(32, 2, true);
  bytes.setUint16(34, 16, true);
  text(36, "data");
  bytes.setUint32(40, samples.length * 2, true);
  let peak = 0;
  for (const sample of samples) peak = Math.max(peak, Math.abs(sample));
  const scale = peak > 0 ? 0.9 / peak : 1;
  samples.forEach((sample, index) => bytes.setInt16(44 + index * 2, Math.max(-1, Math.min(1, sample * scale)) * 0x7fff, true));
  return bytes.buffer;
}

export class Clack {
  constructor() {
    this.context = null;
    this.clips = [];
    this.on = false;
    this.volume = 0.6;
    this.last = 0;
  }

  // Starts audio on the first touch or key, which is when a browser lets a page make sound.
  async wake() {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context || typeof OfflineAudioContext === "undefined") return;
    if (!this.context) {
      this.context = new Context();
      this.out = this.context.createGain();
      this.out.gain.value = this.volume;
      this.out.connect(this.context.destination);
      const rendered = await render(this.context.sampleRate);
      const file = await this.context.decodeAudioData(wav(rendered));
      const length = Math.floor(LENGTH * file.sampleRate);
      const all = file.getChannelData(0);
      for (let variant = 0; variant < VARIANTS; variant += 1) {
        const clip = this.context.createBuffer(1, length, file.sampleRate);
        clip.copyToChannel(all.subarray(variant * length, (variant + 1) * length), 0);
        this.clips.push(clip);
      }
    }
    if (this.context.state === "suspended") await this.context.resume();
  }

  setVolume(value) {
    this.volume = value;
    if (this.out) this.out.gain.setTargetAtTime(value, this.context.currentTime, 0.02);
  }

  // One clack for the modules that turned this frame: louder as more turn at once.
  play(turned, landed) {
    if (!this.on || !this.clips.length || this.context.state !== "running" || this.volume <= 0) return;
    const now = this.context.currentTime;
    if (now - this.last < 0.012) return;
    this.last = now;
    const source = this.context.createBufferSource();
    source.buffer = this.clips[(Math.random() * this.clips.length) | 0];
    source.playbackRate.value = 0.86 + Math.random() * 0.3 - (landed ? 0.06 : 0);
    const level = this.context.createGain();
    level.gain.value = Math.min(1, 0.22 + Math.sqrt(turned) * 0.09 + (landed ? 0.12 : 0));
    source.connect(level).connect(this.out);
    source.start(now);
  }
}
