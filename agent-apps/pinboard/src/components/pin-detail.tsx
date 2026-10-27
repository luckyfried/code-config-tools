import { useState, type CSSProperties } from "react"
import { Check, ExternalLink, FolderInput, Sparkles, X } from "lucide-react"
import { cn } from "cn"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog"
import { MovePicker } from "@/components/move-picker"
import { ACTION_LABEL, eventLine, hostOf, timeWords } from "@/lib/data"
import type { Action, BoardBody, PinView } from "@/types"

interface PinDetailProps {
  pin: PinView | null
  boards: BoardBody[]
  boardName: (id: string | null) => string
  live: boolean
  busy: boolean
  onClose: () => void
  onChoose: (pin: PinView, action: Action, board?: string, name?: string) => void
  onTag: (tag: string) => void
}

/** One pin, large: the image, where it came from, the note, the tags, what the agent noted, and every choice on it. */
export function PinDetail({ pin, boards, boardName, live, busy, onClose, onChoose, onTag }: PinDetailProps) {
  const [broken, setBroken] = useState<string | null>(null)
  return (
    <Dialog open={pin !== null} onOpenChange={(open) => !open && onClose()}>
      {pin && (
        <DialogContent style={{ "--paint": pin.body.color } as CSSProperties} className="max-h-[92dvh] w-[calc(100vw-1.5rem)] max-w-5xl gap-0 overflow-y-auto p-0 sm:max-w-5xl md:grid md:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] md:overflow-hidden">
          <div className="paint flex min-h-40 items-center justify-center md:max-h-[92dvh]">
            {broken !== pin.body.image && (
              <img src={pin.body.image} alt={pin.body.title} onError={() => setBroken(pin.body.image)} className="max-h-[52dvh] w-full object-contain md:max-h-[92dvh]" />
            )}
          </div>
          <div className="flex flex-col gap-5 p-5 md:overflow-y-auto md:p-7">
            <div className="flex flex-col gap-1.5 pr-6">
              <p className="text-sm text-muted-foreground">{pin.board ? boardName(pin.board) : "Unsorted"}</p>
              <DialogTitle className="font-display text-3xl leading-tight font-normal text-balance md:text-4xl">{pin.body.title}</DialogTitle>
              {pin.body.source && (
                <a href={pin.body.source} target="_blank" rel="noreferrer" className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
                  {hostOf(pin.body.source)}
                  <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
            <DialogDescription className={cn("text-base text-pretty text-foreground", !pin.body.note && "sr-only")}>
              {pin.body.note || `A pin from ${hostOf(pin.body.source) || "your agent"}.`}
            </DialogDescription>
            {pin.body.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {pin.body.tags.map((tag) => (
                  <button key={tag} type="button" onClick={() => onTag(tag)} className="min-h-8 rounded-full border border-border px-3 text-sm transition-colors hover:bg-accent">
                    {tag}
                  </button>
                ))}
              </div>
            )}
            {live ? (
              <div className="flex flex-wrap gap-2">
                <Button className="h-11" variant={pin.status === "kept" ? "default" : "outline"} disabled={busy} onClick={() => onChoose(pin, "keep")}>
                  <Check /> {pin.status === "kept" ? "Kept" : ACTION_LABEL.keep}
                </Button>
                <Button className="h-11" variant="outline" disabled={busy} onClick={() => onChoose(pin, "reject")}>
                  <X /> {ACTION_LABEL.reject}
                </Button>
                <MovePicker boards={boards} current={pin.board} disabled={busy} onMove={(board, name) => onChoose(pin, "move", board, name)}>
                  <Button className="h-11" variant="outline" disabled={busy}>
                    <FolderInput /> {ACTION_LABEL.move}
                  </Button>
                </MovePicker>
                <Button className="h-11" variant="outline" disabled={busy} onClick={() => onChoose(pin, "find-more")}>
                  <Sparkles /> {ACTION_LABEL["find-more"]}
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">View only</p>
            )}
            {pin.body.agent_notes.length > 0 && (
              <section className="flex flex-col gap-2">
                <h4 className="text-xs font-medium text-muted-foreground uppercase">From your agent</h4>
                <ul className="flex flex-col gap-1.5 text-sm text-pretty">
                  {pin.body.agent_notes.map((note) => (
                    <li key={note} className="border-l-2 border-asking pl-3">
                      {note}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <section className="flex flex-col gap-2">
              <h4 className="text-xs font-medium text-muted-foreground uppercase">Choices on this pin</h4>
              {pin.history.length === 0 ? (
                <p className="text-sm text-muted-foreground">None yet.</p>
              ) : (
                <ol className="flex flex-col gap-1.5 text-sm">
                  {pin.history.map((event) => (
                    <li key={event.id} className="flex items-baseline justify-between gap-3">
                      <span className={cn("text-pretty", event.status === "cancelled" && "text-muted-foreground line-through")}>{eventLine(event, boardName, pin.found)}</span>
                      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{timeWords(event.at)}</span>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        </DialogContent>
      )}
    </Dialog>
  )
}
