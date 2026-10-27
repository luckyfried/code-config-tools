// Every card in the deck: search the faces, narrow by tag, sort any column, and open one to see its schedule.

import { useEffect, useMemo, useState } from "react"
import { ArrowDown, ArrowUp, Search } from "lucide-react"
import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  tableFeatures,
  useTable,
} from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { allTags, config, type Card, type CardState } from "@/lib/config"
import { daysBetween, monthDay, spanLabel, whenDue } from "@/lib/dates"
import { normalize } from "@/lib/diff"

interface Row {
  card: Card
  s: CardState | undefined
  dueIn: number
}

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, basic: sortFn_basic },
})
const helper = createColumnHelper<typeof features, Row>()

export function BrowseView({ state, now }: { state: Record<string, CardState>; now: string }) {
  const [q, setQ] = useState("")
  const [tag, setTag] = useState<string | null>(null)
  const [cursor, setCursor] = useState(0)
  const [open, setOpen] = useState<Row | null>(null)

  const columns = useMemo(
    () =>
      helper.columns([
        helper.accessor((r) => r.card.front, { id: "front", header: "Front", sortFn: "alphanumeric", cell: (c) => <span className="font-medium">{c.getValue()}</span> }),
        helper.accessor((r) => r.card.back, { id: "back", header: "Back", sortFn: "alphanumeric" }),
        helper.accessor((r) => r.card.tags.join(", "), {
          id: "tags",
          header: "Tags",
          sortFn: "alphanumeric",
          cell: (c) => (
            <span className="flex flex-wrap gap-1">
              {c.row.original.card.tags.map((t) => (
                <Badge key={t} variant="secondary">
                  {t}
                </Badge>
              ))}
            </span>
          ),
        }),
        helper.accessor((r) => r.dueIn, {
          id: "due",
          header: "Next due",
          sortFn: "basic",
          cell: (c) => {
            const r = c.row.original
            return r.s ? <span className={r.dueIn <= 0 ? "font-medium text-warn" : ""}>{whenDue(r.s.due, now)}</span> : <span className="text-muted-foreground">new</span>
          },
        }),
        helper.accessor((r) => r.s?.interval ?? -1, {
          id: "interval",
          header: "Every",
          sortFn: "basic",
          cell: (c) => (c.row.original.s ? spanLabel(c.row.original.s.interval) : "–"),
        }),
        helper.accessor((r) => r.s?.ease ?? 0, {
          id: "ease",
          header: "Ease",
          sortFn: "basic",
          cell: (c) => (c.row.original.s ? c.row.original.s.ease.toFixed(2) : "–"),
        }),
      ]),
    [now],
  )

  const data = useMemo(() => {
    const n = normalize(q)
    return config.cards
      .filter((c) => (!tag || c.tags.includes(tag)) && (!n || normalize(`${c.front} ${c.back} ${c.hint ?? ""}`).includes(n)))
      .map((card) => {
        const s = state[card.id]
        return { card, s, dueIn: s ? daysBetween(now, s.due) : 100000 }
      })
  }, [q, tag, state, now])

  const table = useTable({ features, columns, data, initialState: { sorting: [{ id: "due", desc: false }] } })
  const rows = table.getRowModel().rows

  useEffect(() => setCursor(0), [q, tag])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (open) return
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault()
        setCursor((c) => Math.max(0, Math.min(rows.length - 1, c + (e.key === "ArrowDown" ? 1 : -1))))
      } else if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "BUTTON" && rows[cursor]) {
        setOpen(rows[cursor].original)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [rows, cursor, open])
  useEffect(() => {
    document.querySelector(`[data-row="${cursor}"]`)?.scrollIntoView({ block: "nearest" })
  }, [cursor])

  const hideOnPhone = (id: string) => (id === "tags" || id === "interval" || id === "ease" ? "hidden md:table-cell" : id === "back" ? "hidden sm:table-cell" : "")

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative md:w-80">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the cards" aria-label="Search the cards" className="h-10 bg-card pl-9" />
        </div>
        <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:px-0 md:pb-0">
          <TagChip on={!tag} onClick={() => setTag(null)}>
            All {config.cards.length}
          </TagChip>
          {allTags.map((t) => (
            <TagChip key={t} on={tag === t} onClick={() => setTag(tag === t ? null : t)}>
              {t}
            </TagChip>
          ))}
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border bg-card/80">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id} className="hover:bg-transparent">
                {hg.headers.map((h) => {
                  const sorted = h.column.getIsSorted()
                  return (
                    <TableHead key={h.id} className={hideOnPhone(h.column.id)}>
                      <button type="button" onClick={h.column.getToggleSortingHandler()} className="flex items-center gap-1 font-medium hover:text-foreground">
                        <table.FlexRender header={h} />
                        {sorted === "asc" ? <ArrowUp className="size-3.5" /> : sorted === "desc" ? <ArrowDown className="size-3.5" /> : null}
                      </button>
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {rows.map((r, i) => (
              <TableRow
                key={r.id}
                data-row={i}
                data-state={i === cursor ? "selected" : undefined}
                onClick={() => {
                  setCursor(i)
                  setOpen(r.original)
                }}
                className="cursor-pointer"
              >
                {r.getAllCells().map((c) => (
                  <TableCell key={c.id} className={`py-3 ${hideOnPhone(c.column.id)}`}>
                    <table.FlexRender cell={c} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  No card has “{q}” on it.
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </div>
      <p className="hidden text-xs text-muted-foreground lg:block">↑ and ↓ move through the list · Enter opens a card</p>
      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="sm:max-w-md">
          {open ? (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl">{open.card.front}</DialogTitle>
                <DialogDescription className="text-base text-foreground">{open.card.back}</DialogDescription>
              </DialogHeader>
              {open.card.hint ? <p className="text-sm text-muted-foreground">Hint: {open.card.hint}</p> : null}
              <div className="flex flex-wrap gap-1">
                {open.card.tags.map((t) => (
                  <Badge key={t} variant="secondary">
                    {t}
                  </Badge>
                ))}
              </div>
              <dl className="tnum grid grid-cols-2 gap-2 text-sm">
                <Fact label="Next due" value={open.s ? `${whenDue(open.s.due, now)}${daysBetween(now, open.s.due) > 1 && daysBetween(now, open.s.due) < 14 ? ` (${monthDay(open.s.due)})` : ""}` : "Not seen yet"} />
                <Fact label="Comes back every" value={open.s ? spanLabel(open.s.interval) : "–"} />
                <Fact label="Ease" value={open.s ? open.s.ease.toFixed(2) : "2.50"} />
                <Fact label="Right in a row" value={open.s ? String(open.s.reps) : "0"} />
              </dl>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted px-3 py-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}

function TagChip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={`shrink-0 rounded-full border px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors ${on ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-muted"}`}
    >
      {children}
    </button>
  )
}
