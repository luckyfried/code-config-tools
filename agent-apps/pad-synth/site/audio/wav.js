// A WAV file from an AudioBuffer: 16-bit PCM, the buffer's own channels and sample rate.

export function encodeWav(buffer) {
  const channels = buffer.numberOfChannels;
  const rate = buffer.sampleRate;
  const frames = buffer.length;
  const bytes = frames * channels * 2;
  const view = new DataView(new ArrayBuffer(44 + bytes));
  const text = (at, value) => {
    for (let i = 0; i < value.length; i += 1) view.setUint8(at + i, value.charCodeAt(i));
  };
  text(0, "RIFF");
  view.setUint32(4, 36 + bytes, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * channels * 2, true);
  view.setUint16(32, channels * 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, bytes, true);
  const data = [];
  for (let c = 0; c < channels; c += 1) data.push(buffer.getChannelData(c));
  let at = 44;
  for (let i = 0; i < frames; i += 1) {
    for (let c = 0; c < channels; c += 1) {
      const sample = Math.max(-1, Math.min(1, data[c][i]));
      view.setInt16(at, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      at += 2;
    }
  }
  return new Blob([view.buffer], { type: "audio/wav" });
}
