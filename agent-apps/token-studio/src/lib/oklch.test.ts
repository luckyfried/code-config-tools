// The conversion module checked against published tables: run with `npm test`.
import assert from "node:assert/strict"
import { test } from "node:test"
import { clampChroma, contrast, hexToRgb, oklchToRgb, rgbToHex, rgbToOklch, xyzToOklab, type Rgb } from "./oklch.ts"
import { buildSystem, DEFAULT_SYSTEM } from "./tokens.ts"

const near = (actual: number[], expected: number[], tolerance: number, label: string) =>
  actual.forEach((value, i) =>
    assert.ok(Math.abs(value - expected[i]) <= tolerance, `${label}: got ${actual.map((v) => v.toFixed(4))}, want ${expected}`),
  )

// Björn Ottosson, "A perceptual color space for image processing" (2020), table of XYZ to Oklab test values.
test("XYZ to Oklab matches Ottosson's published table", () => {
  const table: [Rgb, Rgb][] = [
    [[0.95, 1.0, 1.089], [1.0, 0.0, 0.0]],
    [[1.0, 0.0, 0.0], [0.45, 1.236, -0.019]],
    [[0.0, 1.0, 0.0], [0.922, -0.671, 0.263]],
    [[0.0, 0.0, 1.0], [0.153, -1.415, -0.449]],
  ]
  for (const [xyz, lab] of table) near(xyzToOklab(xyz), lab, 0.001, `XYZ ${xyz}`)
})

// The sRGB primaries in OKLCH as CSS Color 4 and oklch.com give them.
test("sRGB primaries round-trip through OKLCH", () => {
  const table: [string, Rgb][] = [
    ["#ff0000", [0.628, 0.2577, 29.23]],
    ["#00ff00", [0.8664, 0.2948, 142.5]],
    ["#0000ff", [0.452, 0.3132, 264.05]],
    ["#ffffff", [1.0, 0.0, 0]],
  ]
  for (const [hex, lch] of table) {
    const rgb = hexToRgb(hex)!
    const got = rgbToOklch(rgb)
    near(got.slice(0, 2), lch.slice(0, 2), 0.001, hex)
    if (lch[1] > 0) near([got[2]], [lch[2]], 0.05, `${hex} hue`)
    assert.equal(rgbToHex(oklchToRgb(...got)), hex)
  }
})

test("contrast follows WCAG 2", () => {
  assert.equal(contrast(hexToRgb("#000")!, hexToRgb("#fff")!).toFixed(2), "21.00")
  assert.equal(contrast(hexToRgb("#777")!, hexToRgb("#fff")!).toFixed(2), "4.48")
})

test("clamping keeps colors inside sRGB", () => {
  const { c, clamped } = clampChroma(0.9, 0.4, 264)
  assert.ok(clamped && c < 0.4)
  assert.ok(oklchToRgb(0.9, c, 264).every((v) => v >= -1e-4 && v <= 1 + 1e-4))
})

test("every ramp has ten steps with falling lightness at every hue", () => {
  for (let hue = 0; hue < 360; hue += 5) {
    const system = buildSystem({ ...DEFAULT_SYSTEM, brand: { hue, chroma: 0.3 } })
    for (const ramp of [system.brand, system.neutral]) {
      assert.equal(ramp.length, 10)
      ramp.slice(1).forEach((step, i) => assert.ok(step.l < ramp[i].l, `hue ${hue} step ${step.name}`))
    }
  }
})
