import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { clientColor, config, money } from "@/lib/config"
import type { Entry } from "@/lib/store"
import { HOUR, msOnDay } from "@/lib/time"

// Hours and their value at each client's rate, for a set of days.
export function ClientTotals({ days, entries, now }: { days: Date[]; entries: Entry[]; now: number }) {
  const rows = config.clients.map((c) => {
    const ms = days.reduce((sum, d) => sum + entries.reduce((s, e) => (e.clientId === c.id ? s + msOnDay(e, d, now) : s), 0), 0)
    return { c, h: ms / HOUR }
  })
  const totalH = rows.reduce((s, r) => s + r.h, 0)
  const totalV = rows.reduce((s, r) => s + r.h * r.c.rate, 0)
  return (
    <Table className="tnum">
      <TableHeader>
        <TableRow>
          <TableHead>Client</TableHead>
          <TableHead className="text-right">Hours</TableHead>
          <TableHead className="hidden text-right sm:table-cell">Rate</TableHead>
          <TableHead className="text-right">Value</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map(({ c, h }) => (
          <TableRow key={c.id}>
            <TableCell>
              <span className="flex items-center gap-2" style={{ "--c": clientColor(c.id) } as React.CSSProperties}>
                <span className="size-2.5 shrink-0 rounded-full bg-(--c)" aria-hidden />
                <span className="truncate">{c.name}</span>
              </span>
            </TableCell>
            <TableCell className="text-right font-mono">{h.toFixed(2)}</TableCell>
            <TableCell className="hidden text-right font-mono text-muted-foreground sm:table-cell">{money.format(c.rate)}</TableCell>
            <TableCell className="text-right font-mono">{money.format(h * c.rate)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
      <TableFooter>
        <TableRow>
          <TableCell className="font-medium">Total</TableCell>
          <TableCell className="text-right font-mono font-medium">{totalH.toFixed(2)}</TableCell>
          <TableCell className="hidden sm:table-cell" />
          <TableCell className="text-right font-mono font-medium">{money.format(totalV)}</TableCell>
        </TableRow>
      </TableFooter>
    </Table>
  )
}
