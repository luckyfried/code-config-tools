import { useRef, type KeyboardEvent, type PointerEvent } from "react"
import { ArrowUpRight, Check, Clock3, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { CompanyMark, PayFigure } from "@/components/card-parts"
import { StateChip } from "@/components/state-chip"
import { applyStage, foundOn, VIEW_ONLY } from "@/lib/board"
import { hue } from "@/lib/company"
import { cn } from "@/lib/utils"
import type { Action, Card } from "@/types"

interface Props {
  card: Card
  // A hero card sits in the pile of new openings; a compact one in a column the person has sorted it into.
  variant: "hero" | "compact"
  // How far down the pile a hero card is: 0 on top.
  depth?: number
  index: number
  intro: boolean
  live: boolean
  phone: boolean
  problem?: string
  busy: boolean
  viewOnly: boolean
  onChoose: (card: Card, action: Action, fromX?: number) => void
  onOpen: (card: Card) => void
}

const SWIPE = 96
// Each choice carries a touch of its column's color.
const TINT: Record<string, string> = {
  yes: "[&_svg]:text-yes hover:bg-yes/10",
  later: "[&_svg]:text-later hover:bg-later/12",
  no: "[&_svg]:text-no hover:bg-no/10",
}

export function JobCard({ card, variant, depth = 0, index, intro, live, phone, problem, busy, viewOnly, onChoose, onOpen }: Props) {
  const { job, shown, latest } = card
  const ref = useRef<HTMLElement | null>(null)
  const drag = useRef<{ x: number; y: number; dx: number; on: boolean } | null>(null)
  // A drag ends with a click on the card; that click is the drag's, not a request to open it.
  const dragged = useRef(false)

  const setVar = (name: string, value: string) => ref.current?.style.setProperty(name, value)
  const place = (el: HTMLElement | null) => {
    ref.current = el
    el?.style.setProperty("--i", String(index))
    el?.style.setProperty("--hue", String(hue(job.company)))
  }

  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.target !== e.currentTarget || e.metaKey || e.ctrlKey || e.altKey) return
    const key = e.key.toLowerCase()
    if (key === "enter" || key === " ") {
      e.preventDefault()
      onOpen(card)
    } else if (!busy && (key === "y" || key === "n" || key === "l")) {
      e.preventDefault()
      onChoose(card, key === "y" ? "yes" : key === "n" ? "no" : "later")
    }
  }

  // The top of the pile, and any card on a phone, follows the finger sideways: right past the line is yes, left is no.
  const down = (e: PointerEvent<HTMLElement>) => {
    dragged.current = false
    if ((variant === "hero" ? depth > 0 : !phone) || busy || e.pointerType === "mouse" && e.button !== 0) return
    if ((e.target as HTMLElement).closest("button, a")) return
    drag.current = { x: e.clientX, y: e.clientY, dx: 0, on: false }
  }
  const move = (e: PointerEvent<HTMLElement>) => {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.x
    const dy = e.clientY - d.y
    if (!d.on) {
      if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) {
        drag.current = null
        return
      }
      if (Math.abs(dx) < 8) return
      d.on = true
      ref.current?.setPointerCapture(e.pointerId)
      ref.current?.setAttribute("data-dragging", "")
    }
    d.dx = dx
    setVar("--dx", `${dx}px`)
    setVar("--dr", `${dx / 40}deg`)
    setVar("--reveal-yes", String(Math.min(1, Math.max(0, dx / SWIPE))))
    setVar("--reveal-no", String(Math.min(1, Math.max(0, -dx / SWIPE))))
  }
  // Ends a drag; returns the drag that ended. `keep` leaves the card where the finger let go, for the flight to take.
  const release = (keep = false) => {
    const d = drag.current
    drag.current = null
    const el = ref.current
    if (!d || !d.on || !el) return null
    dragged.current = true
    el.removeAttribute("data-dragging")
    if (!keep) {
      for (const v of ["--dx", "--dr", "--reveal-yes", "--reveal-no"]) el.style.removeProperty(v)
      el.setAttribute("data-returning", "")
      window.setTimeout(() => el.removeAttribute("data-returning"), 260)
    }
    return d
  }
  const up = () => {
    const d = drag.current
    const action = !d?.on ? null : d.dx > SWIPE && shown !== "yes" ? "yes" : d.dx < -SWIPE && shown !== "no" ? "no" : null
    // A live choice flies the card off from where it was let go; with no board to send to, the card comes back.
    release(!!action && live)
    if (action && d) onChoose(card, action, d.dx)
  }
  const chip = latest?.action === "apply" && latest.status !== "cancelled" ? latest : null
  const note = problem ?? (latest?.status === "failed" ? latest.error : null)
  const hero = variant === "hero"
  const behind = hero && depth > 0
  const choices: { action: Action; label: string; icon: typeof Check; key: string }[] = hero
    ? [
        { action: "no", label: "No", icon: X, key: "N" },
        { action: "later", label: "Later", icon: Clock3, key: "L" },
        { action: "yes", label: "Yes", icon: Check, key: "Y" },
      ]
    : [
        { action: "yes", label: "Yes", icon: Check, key: "Y" },
        { action: "later", label: "Later", icon: Clock3, key: "L" },
        { action: "no", label: "No", icon: X, key: "N" },
      ]
  const remote = job.remote === null ? null : job.remote ? "Remote" : "On site"

  const status = (chip || note) && (
    <div className="flex flex-col items-start gap-1.5">
      {chip && <StateChip stage={applyStage(chip, job)} />}
      {note && <p className="text-[0.8125rem] leading-snug text-destructive">{note}</p>}
    </div>
  )

  const actions = viewOnly ? (
    <p className="mt-auto flex min-h-11 items-center pt-1 text-sm text-muted-foreground">{VIEW_ONLY}</p>
  ) : (
    <div className={cn("mt-auto flex items-center gap-2", hero ? "pt-2" : "pt-1")}>
      {choices
        .filter((c) => c.action !== shown)
        .map(({ action, label, icon: Icon, key }) => (
          <Button
            key={action}
            variant="outline"
            disabled={busy}
            tabIndex={behind ? -1 : undefined}
            onClick={() => onChoose(card, action)}
            className={cn(
              "flex-1 gap-1.5 px-2 font-semibold text-foreground",
              hero ? "h-12 text-[0.9375rem]" : "h-11",
              hero && action === "yes" ? "btn-yes" : TINT[action],
            )}
            aria-keyshortcuts={key}
          >
            <Icon aria-hidden="true" />
            {label}
            {hero && !phone && !behind && (
              <kbd className="key-hint" aria-hidden="true">
                {key}
              </kbd>
            )}
          </Button>
        ))}
      {shown === "yes" && (
        <Button disabled={busy} onClick={() => onChoose(card, "apply")} className="h-11 flex-1 gap-1.5 px-2 font-semibold">
          Apply
          <ArrowUpRight aria-hidden="true" />
        </Button>
      )}
    </div>
  )

  return (
    <div className={cn("relative", hero && "deck-slot")}>
      {phone && !hero && (
        <div className="swipe-under" aria-hidden="true">
          <span className="yes">Yes</span>
          <span className="no">No</span>
        </div>
      )}
      <article
        ref={place}
        data-card={card.record.id}
        data-shown={shown}
        data-variant={variant}
        data-depth={hero ? Math.min(depth, 3) : undefined}
        tabIndex={behind ? -1 : 0}
        aria-hidden={behind || undefined}
        aria-label={`${job.role} at ${job.company}`}
        onKeyDown={onKey}
        onClick={(e) => {
          if (dragged.current) {
            dragged.current = false
            return
          }
          if (!(e.target as HTMLElement).closest("button, a")) onOpen(card)
        }}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={() => release()}
        className={cn(
          "job-card flex h-full cursor-pointer flex-col select-none",
          hero ? "gap-4 p-5 sm:p-6" : "gap-2.5 p-4",
          intro && "card-enter",
        )}
      >
        <span className="card-lift" data-lift aria-hidden="true" />
        {hero ? (
          <>
            <span className="stamp yes" aria-hidden="true">Yes</span>
            <span className="stamp no" aria-hidden="true">No</span>
            <div className="flex items-center gap-3.5">
              <CompanyMark company={job.company} size="lg" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[1rem] font-semibold">{job.company}</p>
                <p className="truncate text-[0.8125rem] text-muted-foreground tabular-nums">Found {foundOn(job.found_at)}</p>
              </div>
              {remote && <span className="place-chip">{remote}</span>}
            </div>
            <h3 className="line-clamp-2 font-heading text-[1.4375rem] leading-[1.15] font-semibold tracking-[-0.015em] text-balance sm:text-[1.5625rem]">
              {job.role}
            </h3>
            {job.pay && (
              <div>
                <PayFigure pay={job.pay} size="lg" />
                <p className="mt-1.5 text-[0.9375rem] text-muted-foreground">{job.location}</p>
              </div>
            )}
            {!job.pay && <p className="text-[0.9375rem] text-muted-foreground">{job.location}</p>}
            {job.facts.length > 0 && (
              <ul className="facts flex flex-col gap-2 text-[0.9375rem] leading-snug text-pretty">
                {job.facts.slice(0, phone ? 2 : 3).map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            )}
            {job.agent_notes[0] && (
              <p className="note px-3.5 py-2.5 text-[0.875rem] leading-snug text-pretty">
                <span className="font-semibold">Your agent: </span>
                {job.agent_notes[0]}
              </p>
            )}
            {status}
            {actions}
          </>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <CompanyMark company={job.company} size="sm" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[0.875rem] font-semibold">{job.company}</p>
                <p className="truncate text-[0.8125rem] text-muted-foreground">
                  {job.location}
                  {remote && ` · ${remote}`}
                </p>
              </div>
              <span className="shrink-0 self-start text-[0.8125rem] text-muted-foreground tabular-nums">{foundOn(job.found_at)}</span>
            </div>
            <h3 className="line-clamp-2 font-heading text-[1.0625rem] leading-[1.2] font-semibold tracking-[-0.01em] text-balance">
              {job.role}
            </h3>
            {job.pay && <PayFigure pay={job.pay} size="md" />}
            {status}
            {actions}
          </>
        )}
      </article>
    </div>
  )
}
