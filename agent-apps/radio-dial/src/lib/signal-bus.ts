import { SPECTRUM_BINS } from './engine'

// What the meters read each frame, from the analyser when a stream allows it, else the synthetic pulse: levels are
// the two needles' places on the VU scale, bins the spectrum heights.
export const levels = new Float32Array(2)
export const bins = new Float32Array(SPECTRUM_BINS)
