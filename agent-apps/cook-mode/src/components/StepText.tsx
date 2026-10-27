import { config, type Recipe } from "@/lib/config"
import { splitDurations } from "@/lib/durations"
import { convertTemperatures } from "@/lib/quantity"
import { TimerChip } from "./TimerChip"

interface StepTextProps {
  recipe: Recipe
  /** Counted from 0. */
  stepIndex: number
  demo?: boolean
}

const TRAILING = /^[.,;:!?)\]…]+/

/** A step's words, with every written duration turned into a timer chip. */
export function StepText({ recipe, stepIndex, demo = false }: StepTextProps) {
  const text = convertTemperatures(recipe.steps[stepIndex] ?? "", config.units)
  const segments = splitDurations(text)
  let demoUsed = false
  return (
    <>
      {segments.map((segment, position) => {
        if (segment.kind === "text") {
          // Punctuation right after a chip is drawn with the chip, below.
          const glued = segments[position - 1]?.kind === "time" ? (segment.text.match(TRAILING)?.[0] ?? "") : ""
          return glued.length < segment.text.length ? <span key={position}>{segment.text.slice(glued.length)}</span> : null
        }
        const showDemo = demo && !demoUsed
        if (showDemo) demoUsed = true
        const next = segments[position + 1]
        const punctuation = next?.kind === "text" ? (next.text.match(TRAILING)?.[0] ?? "") : ""
        const chip = (
          <TimerChip
            key={position}
            recipeId={recipe.id}
            step={stepIndex + 1}
            index={segment.index}
            text={segment.text}
            ms={segment.ms}
            demo={showDemo}
          />
        )
        if (!punctuation) return chip
        // The chip and the stop after it never part across a line break.
        return (
          <span key={position} className="whitespace-nowrap">
            {chip}
            {punctuation}
          </span>
        )
      })}
    </>
  )
}
