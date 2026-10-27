import { useEffect, useId, useRef, type CSSProperties } from "react"
import { cn } from "@/lib/utils"

const BODY =
  "M22 36H118C125 36 129 40 130 47L133 92C133.5 99 129 104 122 104H18C11 104 6.5 99 7 92L10 47C11 40 15 36 22 36Z"
const STRAP = "M50 37V24C50 16 55 12 63 12H77C85 12 90 16 90 24V37"

/** One sine layer from x 0 to 210 with a 60-unit period, so sliding it 60 units loops without a seam. */
function wave(amplitude: number, lift: number) {
  let d = `M0 ${-lift}Q15 ${-lift - amplitude * 2} 30 ${-lift}`
  for (let x = 60; x <= 210; x += 30) d += `T${x} ${-lift}`
  return `${d}V130H0Z`
}
const FRONT = wave(3.5, 0)
const BACK = wave(4.5, 3)

/** The top of the liquid for a packed share from 0 to 1: below the bag when empty, over its rim when full. */
const levelFor = (share: number) => (share <= 0 ? 118 : 104 - share * 76)

/** `mini` is the same bag drawn small on a group header: strokes stay a fixed width and the stitching drops out. */
type BagProps = { share: number; className?: string; label?: string; mini?: boolean }

export function Bag({ share, className, label, mini }: BagProps) {
  const clip = useId()
  const amp = useRef<SVGGElement>(null)
  const tag = useRef<SVGGElement>(null)
  const last = useRef(share)

  useEffect(() => {
    if (last.current === share) return
    const rising = share > last.current
    last.current = share
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return
    amp.current?.getAnimations().forEach((a) => a.cancel())
    amp.current?.animate(
      [
        { transform: "scaleY(1)" },
        { transform: `scaleY(${rising ? 2.3 : 1.8})`, offset: 0.18 },
        { transform: "scaleY(0.7)", offset: 0.48 },
        { transform: "scaleY(1.25)", offset: 0.74 },
        { transform: "scaleY(1)" },
      ],
      { duration: 1500, easing: "ease-out" },
    )
    tag.current?.getAnimations().forEach((a) => a.cancel())
    tag.current?.animate(
      [
        { transform: "rotate(0deg)" },
        { transform: `rotate(${rising ? 12 : -10}deg)`, offset: 0.2 },
        { transform: "rotate(-7deg)", offset: 0.5 },
        { transform: "rotate(3deg)", offset: 0.75 },
        { transform: "rotate(0deg)" },
      ],
      { duration: 1300, easing: "ease-out" },
    )
  }, [share])

  return (
    <svg
      viewBox="0 0 140 114"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn("block overflow-visible", mini && "bag-mini", className)}
    >
      <defs>
        <clipPath id={clip}>
          <path d={BODY} />
        </clipPath>
      </defs>
      <ellipse cx="70" cy="109" rx="58" ry="4" className="fill-[var(--bag-shadow)]" />
      <path d={BODY} className="fill-bag-empty" />
      <g clipPath={`url(#${clip})`}>
        <g className="bag-level" style={{ transform: `translateY(${levelFor(share)}px)` } as CSSProperties}>
          <g ref={amp}>
            <path d={BACK} className="wave wave-back fill-bag-back" />
            <path d={FRONT} className="wave fill-bag" />
          </g>
        </g>
      </g>
      {mini ? null : (
        <>
          <path d="M27 38C23 58 23 82 27 102M113 38C117 58 117 82 113 102" className="fill-none stroke-bag-line/30" strokeWidth="1.5" />
          <path d="M22 48H118" className="fill-none stroke-bag-line/40" strokeWidth="1.5" strokeDasharray="2.5 3" />
        </>
      )}
      <path
        d={BODY}
        className="fill-none stroke-bag-line"
        strokeWidth={mini ? 1.75 : 3.5}
        vectorEffect={mini ? "non-scaling-stroke" : undefined}
        strokeLinejoin="round"
      />
      <path
        d={STRAP}
        className="fill-none stroke-bag-line"
        strokeWidth={mini ? 2.25 : 5.5}
        vectorEffect={mini ? "non-scaling-stroke" : undefined}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <rect x="59" y="8.5" width="22" height="7.5" rx="3.75" className="fill-bag-line" />
      <g ref={tag} className="[transform-origin:90px_30px]">
        <path d="M90 30L98 41" className="fill-none stroke-bag-line" strokeWidth={mini ? 1 : 1.5} vectorEffect={mini ? "non-scaling-stroke" : undefined} strokeLinecap="round" />
        <rect x="93" y="40" width="15" height="21" rx="3.5" className="fill-primary stroke-bag-line" strokeWidth={mini ? 1 : 1.5} vectorEffect={mini ? "non-scaling-stroke" : undefined} transform="rotate(-8 100 50)" />
        <circle cx="99.6" cy="44.6" r="1.6" className="fill-bag-line" />
      </g>
    </svg>
  )
}
