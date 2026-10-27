import type { CSSProperties } from "react"
import { X } from "lucide-react"
import { cn } from "cn"
import type { BoardBody, Filter, PinView } from "@/types"

interface ShelvesProps {
  boards: BoardBody[]
  pins: PinView[]
  filter: Filter
  onFilter: (filter: Filter) => void
  register: (id: string, el: HTMLElement | null) => void
}

interface Shelf {
  id: string
  label: string
  filter: Filter
  pins: PinView[]
}

/** The row of boards under the title: each a shelf with its count and a strip of its pins' colors. */
export function Shelves({ boards, pins, filter, onFilter, register }: ShelvesProps) {
  const onWall = pins.filter((pin) => pin.status !== "rejected")
  const shelves: Shelf[] = [
    { id: "all", label: "Everything", filter: { kind: "all" }, pins: onWall },
    ...boards.map((board) => ({
      id: board.id,
      label: board.name,
      filter: { kind: "board", id: board.id } as Filter,
      pins: onWall.filter((pin) => pin.board === board.id),
    })),
  ]
  const unsorted = onWall.filter((pin) => !pin.board || !boards.some((board) => board.id === pin.board))
  if (unsorted.length > 0) shelves.push({ id: "unsorted", label: "Unsorted", filter: { kind: "unsorted" }, pins: unsorted })
  const aside = pins.filter((pin) => pin.status === "rejected")
  shelves.push({ id: "set-aside", label: "Set aside", filter: { kind: "set-aside" }, pins: aside })

  const active = (shelf: Shelf) => {
    if (filter.kind === "board" && shelf.filter.kind === "board") return filter.id === shelf.filter.id
    return filter.kind === shelf.filter.kind && filter.kind !== "board"
  }

  return (
    <nav aria-label="Boards" className="shelf-row -mx-4 flex snap-x scroll-px-4 gap-2 overflow-x-auto px-4 pb-1 md:-mx-8 md:scroll-px-8 md:px-8">
      {shelves.map((shelf) => (
        <button
          key={shelf.id}
          ref={(el) => register(shelf.id, el)}
          type="button"
          aria-pressed={active(shelf)}
          onClick={() => onFilter(shelf.filter)}
          className={cn(
            "flex min-h-11 shrink-0 snap-start items-center gap-2.5 rounded-full border border-border bg-card py-1.5 pr-3.5 pl-1.5 text-sm transition-colors hover:bg-accent",
            active(shelf) && "border-foreground bg-foreground text-background hover:bg-foreground",
            shelf.id === "set-aside" && shelf.pins.length === 0 && !active(shelf) && "text-muted-foreground",
          )}
        >
          <span className="flex h-8 w-8 shrink-0 overflow-hidden rounded-full bg-muted ring-1 ring-swatch-ring" aria-hidden="true">
            {shelf.pins.slice(0, 3).map((pin) => (
              <span key={pin.id} className="paint h-full flex-1" style={{ "--paint": pin.body.color } as CSSProperties} />
            ))}
          </span>
          <span className="font-medium whitespace-nowrap">{shelf.label}</span>
          <span className={cn("tabular-nums", active(shelf) ? "text-background/70" : "text-muted-foreground")}>{shelf.pins.length}</span>
        </button>
      ))}
      {filter.kind === "tag" && (
        <button
          type="button"
          onClick={() => onFilter({ kind: "all" })}
          className="flex min-h-11 shrink-0 items-center gap-2 rounded-full border border-foreground bg-foreground px-4 text-sm font-medium text-background"
          aria-label={`Showing pins tagged ${filter.tag}; show everything`}
        >
          #{filter.tag}
          <X className="size-4" />
        </button>
      )}
      <span className="w-6 shrink-0 md:w-10" aria-hidden="true" />
    </nav>
  )
}
