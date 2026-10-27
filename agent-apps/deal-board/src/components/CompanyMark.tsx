import { hueOf, initialOf, shapeOf } from "@/lib/format"
import { cn } from "@/lib/utils"

const SHAPES = [
  <circle key="0" className="mark-shape" cx="40" cy="40" r="21" />,
  <path key="1" className="mark-shape" d="M0 40 L40 12 L40 40 Z" />,
  <rect key="2" className="mark-shape" x="0" y="27" width="40" height="13" />,
  <circle key="3" className="mark-shape" cx="35" cy="5" r="15" />,
]

/** A company's mark: its initial in white on a lit disc in its own hue, with a deeper shape behind the letter. */
export function CompanyMark({ company, className, muted }: { company: string; className?: string; muted?: boolean }) {
  const name = company.trim() || "?"
  return (
    <span
      data-mark=""
      style={{ "--hue": hueOf(name) } as React.CSSProperties}
      className={cn("relative grid shrink-0 place-items-center overflow-hidden rounded-full font-semibold tracking-[-0.02em]", muted && "opacity-60 saturate-[0.35]", className)}
    >
      <svg viewBox="0 0 40 40" className="absolute inset-0 size-full" aria-hidden="true">
        {SHAPES[shapeOf(name)]}
      </svg>
      <span className="relative">{initialOf(name)}</span>
    </span>
  )
}
