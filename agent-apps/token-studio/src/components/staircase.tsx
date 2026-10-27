import { memo } from "react"
import type { System } from "@/lib/tokens"

/** The type scale as a staircase: each step's sample sits on a baseline raised by its own size. */
export const Staircase = memo(function Staircase({ type }: { type: System["type"] }) {
  return (
    <figure className="offscreen-skip flex flex-col gap-3">
      <figcaption className="section-label">
        The scale
        <span className="text-xs font-normal text-muted-foreground tabular-nums">
          {Math.round(type[0].px)} to {Math.round(type[type.length - 1].px)} px
        </span>
      </figcaption>
      <ol className="stairs" data-live="type font">
        {type.map((t) => (
          <li key={t.name} className="stair" data-step={t.name}>
            <span className="stair-area">
              <span className="stair-riser" />
              <span className="stair-glyph" aria-hidden="true">
                A
              </span>
            </span>
            <span className="stair-name font-mono">{t.name}</span>
            <span className="stair-px font-mono tabular-nums">{Math.round(t.px)}</span>
          </li>
        ))}
      </ol>
    </figure>
  )
})
