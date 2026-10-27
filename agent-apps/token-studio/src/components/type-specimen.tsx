import { memo } from "react"
import { cn } from "@/lib/utils"

/** Real paragraphs set in the scale; they ease to each new size. */
export const TypeSpecimen = memo(function TypeSpecimen({ className }: { className?: string }) {
  return (
    <article className={cn("specimen", className)}>
      <p className="specimen-kicker">Spring field guide</p>
      <h2 className="specimen-display">Walk the ridge before the light goes gold.</h2>
      <p className="specimen-lead">
        Four routes north of the river, each under three hours, each ending somewhere worth sitting down.
      </p>
      <p className="specimen-body">
        Start at the old quarry lot and keep the creek on your left. The first mile climbs through birch and fern; after
        the second footbridge the trees open and the whole valley turns to face you. Bring a layer: the wind on the
        saddle is ten degrees cooler than the trailhead.
      </p>
      <p className="specimen-small">
        Route notes by the trail crew, set in <code className="specimen-code">--text-sm</code>.
      </p>
    </article>
  )
})
