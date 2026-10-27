import { useId } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

type Props = { face: "light" | "dark"; compact?: boolean }

const STARS = [
  [34, 30, 1.4],
  [72, 62, 1],
  [118, 22, 1.2],
  [164, 48, 0.9],
  [212, 18, 1.3],
  [248, 70, 0.8],
  [336, 34, 1.1],
  [372, 76, 0.9],
  [92, 96, 0.8],
  [190, 88, 1],
] as const

/** A walking-series poster painted only with the generated tokens: the ramp is its landscape, the scale its type. */
export function Poster({ face, compact = false }: Props) {
  const uid = useId()
  const sky = `${uid}-sky`
  const night = face === "dark"
  return (
    <Card className="poster" data-face={face} data-compact={compact ? "" : undefined}>
      <div className="poster-top">
        <span>Fieldnote Walks</span>
        <span className="tabular-nums">No. 04</span>
      </div>
      <div className="poster-art" aria-hidden="true">
        <svg viewBox="0 0 400 220" preserveAspectRatio="xMidYMax slice">
          <defs>
            <linearGradient id={sky} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" className="poster-sky-top" />
              <stop offset="1" className="poster-sky-low" />
            </linearGradient>
          </defs>
          <rect width="400" height="220" fill={`url(#${sky})`} />
          {night ? STARS.map(([x, y, r]) => <circle key={`${x}-${y}`} className="poster-star" cx={x} cy={y} r={r} />) : null}
          <circle className="poster-sun-halo" cx="292" cy="112" r="64" />
          <circle className="poster-sun" cx="292" cy="112" r="40" />
          <path className="poster-ridge-1" d="M0 148 C 52 118 104 124 158 140 S 256 104 318 126 S 382 118 400 124 V 220 H 0 Z" />
          <path className="poster-ridge-2" d="M0 170 C 46 150 118 142 182 160 S 302 146 400 138 V 220 H 0 Z" />
          <path className="poster-trail" d="M18 167 C 70 150 120 146 182 160 S 292 148 360 141" />
          <path className="poster-ridge-3" d="M0 192 C 82 168 150 174 222 186 S 336 166 400 174 V 220 H 0 Z" />
          <path className="poster-ridge-4" d="M0 212 C 92 194 196 202 262 208 S 358 198 400 204 V 220 H 0 Z" />
        </svg>
        <span className="poster-stamp">
          <span className="poster-stamp-big tabular-nums">4</span>
          <span>new routes</span>
        </span>
      </div>
      <div className="poster-copy">
        <p className="poster-kicker">Spring series, {night ? "by moonlight" : "at first light"}</p>
        <h3 className="poster-title">
          Ridge
          <br />
          Line
        </h3>
        <p className="poster-sub">Four dawn walks north of the river. Coffee waits at the top.</p>
      </div>
      {compact ? null : (
        <dl className="poster-meta">
          <div>
            <dt>Meet</dt>
            <dd>Quarry lot, 6:10</dd>
          </div>
          <div>
            <dt>Length</dt>
            <dd className="tabular-nums">Under 3 hrs</dd>
          </div>
          <div>
            <dt>Bring</dt>
            <dd>A warm layer</dd>
          </div>
        </dl>
      )}
      <form className="poster-form" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor={`${uid}-email`} className="sr-only">
          Email
        </label>
        <Input id={`${uid}-email`} type="email" placeholder="you@studio.com" autoComplete="off" />
        <Button type="submit" size="lg" className="poster-cta">
          Save my spot
        </Button>
      </form>
    </Card>
  )
}
