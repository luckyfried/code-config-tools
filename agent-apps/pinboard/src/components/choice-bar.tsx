import type { SyntheticEvent } from "react"
import { Check, FolderInput, Sparkles, X } from "lucide-react"
import { cn } from "cn"
import { MovePicker } from "@/components/move-picker"
import type { Action, BoardBody, PinView } from "@/types"

interface ChoiceBarProps {
  pin: PinView
  boards: BoardBody[]
  live: boolean
  busy: boolean
  open: boolean
  onChoose: (action: Action, board?: string, name?: string) => void
}

const base =
  "flex size-11 items-center justify-center rounded-full bg-card/95 text-card-foreground shadow-sm ring-1 ring-border transition-[transform,background-color] duration-150 ease-out hover:scale-105 active:scale-95 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:opacity-60 disabled:hover:scale-100"

/**
 * Keep, set aside, move, and more like this: shown on hover with a mouse and after a long press on a phone, where
 * they sit two by two over the dimmed picture so each is a 44 px thumb target. A page without its server shows
 * "View only" in their place.
 */
export function ChoiceBar({ pin, boards, live, busy, open, onChoose }: ChoiceBarProps) {
  const stop = (event: SyntheticEvent) => event.stopPropagation()
  return (
    <div
      data-open={open}
      onClick={stop}
      onPointerDown={stop}
      className={cn(
        "pointer-events-none absolute inset-0 grid grid-cols-[auto_auto] place-content-center gap-2 bg-black/30 opacity-0 transition-opacity duration-150 ease-out",
        "md:top-auto md:flex md:items-center md:justify-center md:bg-transparent md:bg-gradient-to-t md:from-black/35 md:to-transparent md:px-2 md:pt-8 md:pb-2.5",
        "group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100",
        "data-[open=true]:pointer-events-auto data-[open=true]:opacity-100",
      )}
    >
      {!live ? (
        <span className="col-span-2 rounded-full bg-card/90 px-3 py-1.5 text-xs text-muted-foreground shadow-sm">View only</span>
      ) : (
        <>
          <button type="button" className={cn(base, pin.status === "kept" && "bg-kept text-kept-foreground ring-kept")} disabled={busy} aria-label={`Keep ${pin.body.title}`} onClick={() => onChoose("keep")}>
            <Check className="size-5" />
          </button>
          <button type="button" className={base} disabled={busy} aria-label={`Set aside ${pin.body.title}`} onClick={() => onChoose("reject")}>
            <X className="size-5" />
          </button>
          <MovePicker boards={boards} current={pin.board} disabled={busy} onMove={(board, name) => onChoose("move", board, name)}>
            <button type="button" className={base} disabled={busy} aria-label={`Move ${pin.body.title} to a board`}>
              <FolderInput className="size-5" />
            </button>
          </MovePicker>
          <button type="button" className={cn(base, pin.asking && "bg-asking text-white ring-asking")} disabled={busy} aria-label={`Ask for more like ${pin.body.title}`} onClick={() => onChoose("find-more")}>
            <Sparkles className="size-5" />
          </button>
        </>
      )}
    </div>
  )
}
