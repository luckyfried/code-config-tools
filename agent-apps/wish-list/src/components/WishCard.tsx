import { memo, useState } from "react"
import { ArrowUpRight, Gift, Undo2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RollingNumber } from "@/components/RollingNumber"
import { fill, type Copy, type Item } from "@/lib/config"
import { useThumb } from "@/lib/thumbs"
import { cn } from "@/lib/utils"

export type CardState = "open" | "gotten" | "yours"

function store(url: string | undefined): string | null {
  if (!url) return null
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return null
  }
}

/** The tag a gotten card wears over its picture: it folds down from the top and a stamp lands on it. */
function GiftTag({ yours, copy, owner, delay }: { yours: boolean; copy: Copy; owner: string; delay: number }) {
  const [start] = useState(delay)
  const style = { "--fold-delay": `${start}ms` } as React.CSSProperties
  return (
    <div className="absolute inset-0 z-[4] [perspective:900px]" style={style}>
      <div className="tag fold-in">
        <span className="tag-hole" />
        <span className={cn("stamp stamp-in", yours && "is-yours")}>{yours ? copy.yours : copy.gotten}</span>
        {yours && (
          <p className="absolute inset-x-0 bottom-[12%] text-center text-[0.82rem] font-medium text-tag-muted">
            {fill(copy.yoursNote, { owner })}
          </p>
        )}
      </div>
      <svg className="tag-string string-in" viewBox="0 0 52 46" aria-hidden="true">
        <path d="M14 0 C 14 22, 26 30, 26 38 M38 0 C 38 22, 26 30, 26 38" strokeWidth={2.5} strokeLinecap="round" />
      </svg>
    </div>
  )
}

export const WishCard = memo(function WishCard({
  item,
  state,
  format,
  turn,
  copy,
  owner,
  foldDelay,
  slotRef,
  tiltRef,
  onGet,
  onUndo,
  onPicture,
}: {
  item: Item
  state: CardState
  format: Intl.NumberFormat
  turn: number
  copy: Copy
  owner: string
  foldDelay: number
  slotRef: (el: HTMLDivElement | null) => void
  tiltRef: (el: HTMLDivElement | null) => void
  onGet: (item: Item) => void
  onUndo: (item: Item) => void
  onPicture: (item: Item, thumb: string | null) => void
}) {
  const thumb = useThumb(item.image)
  const host = store(item.url)
  const gotten = state !== "open"
  return (
    <div ref={slotRef} className="deal-slot" data-id={item.id}>
      <div ref={tiltRef} className="tilt h-full">
        <article className={cn("wish-card flex flex-col", gotten && "is-gotten")} aria-label={item.name}>
          <div className="relative">
            <button
              type="button"
              className="stage block w-full text-left focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              onClick={() => onPicture(item, thumb)}
              aria-label={item.image ? `${item.name}, full size` : item.name}
            >
              <span className="plinth" />
              {item.image ? (
                <img
                  className="picture"
                  src={thumb ?? undefined}
                  data-ready={thumb ? "true" : "false"}
                  alt=""
                  draggable={false}
                  decoding="async"
                />
              ) : (
                <Gift className="picture text-primary/70" strokeWidth={1.1} />
              )}
              {item.priority === "high" && !gotten && (
                <Badge className="absolute top-3 left-3 z-[2] h-6 px-2.5 text-[0.72rem] font-semibold tracking-wide shadow-sm">
                  {copy.mostWanted}
                </Badge>
              )}
            </button>
            {gotten && <GiftTag yours={state === "yours"} copy={copy} owner={owner} delay={foldDelay} />}
          </div>
          <div className="flex flex-1 flex-col gap-1.5 px-4 pt-3.5 pb-4">
            <div className="flex items-start justify-between gap-3">
              <h2 className="display text-[1.14rem] leading-snug font-semibold">{item.name}</h2>
              <RollingNumber
                value={item.price}
                format={format}
                turn={turn}
                className={cn(
                  "display shrink-0 pt-0.5 text-[1.18rem] font-semibold text-primary",
                  gotten && "text-muted-foreground line-through decoration-2",
                )}
              />
            </div>
            {item.note && <p className="text-[0.88rem] leading-snug text-muted-foreground">{item.note}</p>}
            <div className="mt-auto flex flex-wrap items-center justify-between gap-x-2 gap-y-2 pt-3">
              {host ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-0.5 rounded-md py-1 text-[0.8rem] whitespace-nowrap text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                  <span>{host}</span>
                  <ArrowUpRight className="size-3.5 shrink-0" />
                </a>
              ) : (
                <span />
              )}
              {state === "open" && (
                <Button size="sm" className="ml-auto h-9 shrink-0 gap-1 rounded-full px-3 font-semibold" onClick={() => onGet(item)}>
                  <Gift className="size-4" />
                  {copy.getThis}
                </Button>
              )}
              {state === "yours" && (
                <Button size="sm" variant="ghost" className="h-9 shrink-0 gap-1.5 rounded-full" onClick={() => onUndo(item)}>
                  <Undo2 className="size-4" />
                  {copy.undo}
                </Button>
              )}
              {state === "gotten" && (
                <span className="h-9 shrink-0 px-1 text-[0.84rem] leading-9 font-medium text-muted-foreground">{copy.gottenShort}</span>
              )}
            </div>
          </div>
          <div className="sheen" aria-hidden="true">
            <span className="sheen-band" />
            <span className="glare" />
          </div>
        </article>
      </div>
    </div>
  )
})
