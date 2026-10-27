import { useEffect, useState } from "react"
import type { Topic } from "@/types"
import { useMedia } from "@/hooks/use-media"

type Rgb = [number, number, number]

let probe: CanvasRenderingContext2D | null = null

/** Any CSS color as sRGB channels from 0 to 1, read back from one painted pixel. */
function rgb(color: string): Rgb {
  probe ??= document.createElement("canvas").getContext("2d", { willReadFrequently: true })
  if (!probe) return [0, 0, 0]
  probe.clearRect(0, 0, 1, 1)
  probe.fillStyle = color
  probe.fillRect(0, 0, 1, 1)
  const [r, g, b] = probe.getImageData(0, 0, 1, 1).data
  return [r / 255, g / 255, b / 255]
}

const mix = (a: Rgb, b: Rgb, t: number): Rgb => [0, 1, 2].map((i) => a[i] + (b[i] - a[i]) * t) as Rgb

/**
 * One SVG filter per topic, `#duo-<topic id>`: the picture's lightness mapped from the theme's ink, through the
 * topic's color, to the theme's light paper tinted by the topic. The theme decides the ends, so a theme change
 * redraws every picture.
 */
export function DuotoneFilters({ topics }: { topics: Topic[] }) {
  const dark = useMedia("(prefers-color-scheme: dark)")
  const [ends, setEnds] = useState<{ ink: Rgb; light: Rgb } | null>(null)

  useEffect(() => {
    const css = getComputedStyle(document.documentElement)
    document.documentElement.dataset.scheme = css.getPropertyValue("--scheme").trim() || "light"
    setEnds({ ink: rgb(css.getPropertyValue("--duo-ink").trim()), light: rgb(css.getPropertyValue("--duo-light").trim()) })
  }, [dark])

  if (!ends) return null
  return (
    <svg className="absolute size-0 overflow-hidden" aria-hidden="true" focusable="false">
      {topics.map((t) => {
        const paint = rgb(t.color)
        const light = mix(ends.light, paint, 0.22)
        const table = (i: number) => [ends.ink[i], mix(ends.ink, paint, 0.55)[i], paint[i], light[i]].map((v) => v.toFixed(3)).join(" ")
        return (
          <filter key={t.id} id={`duo-${t.id}`} colorInterpolationFilters="sRGB" x="0" y="0" width="1" height="1">
            <feColorMatrix
              type="matrix"
              values="0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0 0 0 1 0"
            />
            <feComponentTransfer>
              <feFuncR type="table" tableValues={table(0)} />
              <feFuncG type="table" tableValues={table(1)} />
              <feFuncB type="table" tableValues={table(2)} />
            </feComponentTransfer>
          </filter>
        )
      })}
    </svg>
  )
}
