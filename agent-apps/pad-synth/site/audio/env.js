// Envelope helpers shared by the voices.

/** Holds `param` at whatever value it has at `time`, so a release starts from where the sound is. */
export function holdAt(param, time) {
  if (typeof param.cancelAndHoldAtTime === "function") {
    param.cancelAndHoldAtTime(time);
  } else {
    param.cancelScheduledValues(time);
    param.setValueAtTime(param.value, time);
  }
}

/** Fades `param` toward zero from `time` with time constant `tau` (about 99% gone after 4.6 tau). */
export function fadeOut(param, time, tau) {
  holdAt(param, time);
  param.setTargetAtTime(0, time, tau);
}

/** A soft saturation curve for a WaveShaper, `drive` above 1 for more. */
export function softClip(drive, size = 1024) {
  const curve = new Float32Array(size);
  const norm = Math.tanh(drive);
  for (let i = 0; i < size; i += 1) {
    const x = (i / (size - 1)) * 2 - 1;
    curve[i] = Math.tanh(drive * x) / norm;
  }
  return curve;
}
