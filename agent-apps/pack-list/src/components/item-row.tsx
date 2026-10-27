import { memo, useRef, type PointerEvent } from "react"
import { CheckIcon, RotateCcwIcon, XIcon } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import type { Item } from "@/lib/config"
import { cn } from "@/lib/utils"

/** A swipe starts only after the finger has moved this far sideways, so scrolling the list never checks a row. */
const DEAD_ZONE = 12

type ItemRowProps = {
  item: Item
  packed: boolean
  showWeight: boolean
  fresh: boolean
  onToggle: (key: string) => void
  onRemove: (key: string) => void
}

export const ItemRow = memo(function ItemRow({ item, packed, showWeight, fresh, onToggle, onRemove }: ItemRowProps) {
  const row = useRef<HTMLLIElement>(null)
  const face = useRef<HTMLDivElement>(null)
  const drag = useRef<{ id: number; x: number; y: number; mode: "pending" | "drag" | "scroll"; dx: number } | null>(null)
  const swallowClick = useRef(false)
  const id = `item-${item.key.replace(/[^a-z0-9]+/g, "-")}`

  const threshold = () => Math.min(104, (row.current?.offsetWidth ?? 320) * 0.3)

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return
    drag.current = { id: e.pointerId, x: e.clientX, y: e.clientY, mode: "pending", dx: 0 }
  }

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId || d.mode === "scroll") return
    const dx = e.clientX - d.x
    const dy = e.clientY - d.y
    if (d.mode === "pending") {
      if (Math.abs(dy) > DEAD_ZONE && Math.abs(dy) > Math.abs(dx)) {
        d.mode = "scroll"
        return
      }
      if (dx > DEAD_ZONE && dx > Math.abs(dy)) {
        d.mode = "drag"
        face.current?.setPointerCapture(e.pointerId)
        face.current?.classList.add("is-dragging")
      } else return
    }
    const pull = Math.max(0, dx - DEAD_ZONE)
    const limit = threshold()
    const shown = pull <= limit ? pull : limit + (pull - limit) * 0.35
    d.dx = pull
    face.current?.style.setProperty("transform", `translateX(${shown}px)`)
    row.current?.toggleAttribute("data-armed", pull >= limit)
    row.current?.style.setProperty("--pull", String(Math.min(1, pull / limit)))
  }

  const finish = (e: PointerEvent<HTMLDivElement>, cancelled: boolean) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    drag.current = null
    if (d.mode !== "drag") return
    swallowClick.current = true
    setTimeout(() => (swallowClick.current = false), 0)
    face.current?.classList.remove("is-dragging")
    face.current?.style.setProperty("transform", "translateX(0px)")
    row.current?.removeAttribute("data-armed")
    row.current?.style.setProperty("--pull", "0")
    if (!cancelled && d.dx >= threshold()) onToggle(item.key)
  }

  return (
    <li
      ref={row}
      data-flip-key={item.key}
      className={cn("group/row swipe-row relative overflow-hidden", packed && "is-packed", fresh && "row-in")}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 flex items-center gap-2 bg-swipe pl-5 text-sm font-semibold text-swipe-foreground opacity-[calc(0.35+var(--pull,0)*0.65)]"
      >
        <span className="grid size-7 place-items-center rounded-full bg-swipe-foreground/15 transition-transform duration-150 group-data-armed/row:scale-115">
          {packed ? <RotateCcwIcon className="size-4" /> : <CheckIcon className="size-4" />}
        </span>
        {packed ? "Unpack" : "Packed"}
      </div>
      <div
        ref={face}
        className="swipe-face row-hoverable relative flex min-h-12 items-center gap-3 bg-card pr-2 pl-4"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={(e) => finish(e, false)}
        onPointerCancel={(e) => finish(e, true)}
        onClickCapture={(e) => {
          if (swallowClick.current) {
            e.preventDefault()
            e.stopPropagation()
          }
        }}
      >
        <Checkbox id={id} checked={packed} onCheckedChange={() => onToggle(item.key)} />
        <label
          htmlFor={id}
          className="flex min-h-12 min-w-0 flex-1 cursor-pointer items-center py-2 text-base select-none"
        >
          <span
            className={cn(
              "strike text-pretty",
              packed ? "text-muted-foreground" : "text-foreground",
            )}
          >
            {item.name}
          </span>
        </label>
        {showWeight && item.weight !== null ? (
          <span className={cn("shrink-0 text-sm tabular-nums text-muted-foreground", packed && "opacity-60")}>
            {item.weight < 1 ? `${Math.round(item.weight * 1000)} g` : `${item.weight.toFixed(1)} kg`}
          </span>
        ) : null}
        {item.added ? (
          <button
            type="button"
            onClick={() => onRemove(item.key)}
            aria-label={`Take ${item.name} off the list`}
            className="grid size-10 shrink-0 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            <XIcon className="size-4" />
          </button>
        ) : (
          <span className="w-2 shrink-0" />
        )}
      </div>
    </li>
  )
})
