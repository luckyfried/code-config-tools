import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState } from "@tanstack/react-table"
import { ArrowDownIcon, ArrowUpIcon, ChevronsUpDownIcon } from "lucide-react"
import { useMemo, useState } from "react"
import { AgeRing } from "@/components/AgeRing"
import { CompanyMark } from "@/components/CompanyMark"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { dayLabel, money, plural } from "@/lib/format"
import { LOST, WON, daysInStage, isClosed, type Deal, type Stage } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

/** Every deal in one table, sortable by value, age, and next step. */
export function ListView({ deals, stages, now, onOpen }: { deals: Deal[]; stages: Stage[]; now: number; onOpen: (id: string) => void }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "value", desc: true }])
  const stageOf = useMemo(() => new Map(stages.map((stage, i) => [stage.id, { ...stage, order: i }])), [stages])
  const columns = useMemo<ColumnDef<Deal>[]>(
    () => [
      {
        id: "company",
        header: "Company",
        accessorKey: "company",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="flex min-w-0 items-center gap-3">
            <CompanyMark company={row.original.company} className="size-8 text-sm" />
            <span className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{row.original.company}</span>
              <span className="truncate text-[13px] text-muted-foreground md:hidden">{stageLabel(row.original.stage)}</span>
            </span>
          </span>
        ),
      },
      {
        id: "stage",
        header: "Stage",
        accessorFn: (deal) => (deal.stage === WON ? 100 : deal.stage === LOST ? 101 : stageOf.get(deal.stage)?.order ?? 0),
        enableSorting: false,
        cell: ({ row }) => {
          const stage = stageOf.get(row.original.stage)
          return (
            <span data-stage="" style={stage ? ({ "--stage-raw": stage.color } as React.CSSProperties) : undefined} className="flex items-center gap-2 whitespace-nowrap">
              <span className={cn("size-2 rounded-full", row.original.stage === WON ? "bg-won" : row.original.stage === LOST ? "bg-lost" : "bg-stage")} />
              {stageLabel(row.original.stage)}
            </span>
          )
        },
      },
      {
        id: "value",
        header: "Value",
        accessorKey: "value",
        sortDescFirst: true,
        cell: ({ row }) => <span className="font-medium tabular-nums">{money(row.original.value)}</span>,
      },
      {
        id: "weighted",
        header: "Weighted",
        accessorFn: (deal) => (deal.value * (stageOf.get(deal.stage)?.probability ?? 0)) / 100,
        enableSorting: false,
        cell: ({ getValue }) => <span className="tabular-nums text-muted-foreground">{money(getValue<number>())}</span>,
      },
      {
        id: "age",
        header: "Age",
        accessorFn: (deal) => (isClosed(deal) ? -1 : daysInStage(deal, now)),
        sortDescFirst: true,
        cell: ({ row }) =>
          isClosed(row.original) ? (
            <span className="text-muted-foreground">
              <span className="sm:hidden">Done</span>
              <span className="max-sm:hidden">Closed</span>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 whitespace-nowrap tabular-nums">
              <AgeRing days={daysInStage(row.original, now)} />
              <span className="sm:hidden">{daysInStage(row.original, now)}d</span>
              <span className="max-sm:hidden">{plural(daysInStage(row.original, now), "day")}</span>
            </span>
          ),
      },
      {
        id: "next",
        header: "Next step",
        // Dated steps first, soonest first; then undated ones by name.
        accessorFn: (deal) => `${deal.date || "9999-99-99"} ${deal.nextStep.toLowerCase()}`,
        sortUndefined: "last",
        cell: ({ row }) => (
          <span className="flex min-w-0 flex-col">
            <span className="truncate">{row.original.nextStep || (isClosed(row.original) ? null : <span className="text-muted-foreground">None yet</span>)}</span>
            {row.original.date ? <span className="text-[13px] text-muted-foreground tabular-nums">by {dayLabel(row.original.date)}</span> : null}
          </span>
        ),
      },
      { id: "contact", header: "Contact", accessorKey: "contact", enableSorting: false, cell: ({ getValue }) => <span className="truncate">{getValue<string>()}</span> },
    ],
    [stageOf, now],
  )
  function stageLabel(id: string) {
    return id === WON ? "Won" : id === LOST ? "Lost" : stageOf.get(id)?.label ?? id
  }
  const table = useReactTable({ data: deals, columns, state: { sorting }, onSortingChange: setSorting, getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel() })
  const hidden: Record<string, string> = { stage: "hidden md:table-cell", weighted: "hidden lg:table-cell", contact: "hidden xl:table-cell", next: "hidden sm:table-cell" }

  return (
    <div className="w-full px-4 pt-2 pb-8 sm:px-6">
      <div className="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-xl font-semibold">Every deal</h2>
        <span className="text-sm text-muted-foreground">{plural(deals.length, "deal")}, sorted by {sortName(sorting)}</span>
      </div>
      <div className="overflow-hidden rounded-2xl border bg-card">
        <Table className="table-fixed">
          <TableHeader>
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id} className="hover:bg-transparent">
                {group.headers.map((header) => {
                  const sorted = header.column.getIsSorted()
                  return (
                    <TableHead
                      key={header.id}
                      aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                      className={cn(
                        "h-11 px-4",
                        hidden[header.id],
                        WIDTHS[header.id],
                        (header.id === "value" || header.id === "weighted") && "text-right",
                      )}
                    >
                      {header.column.getCanSort() ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className={cn("inline-flex h-9 items-center gap-1 rounded-md hover:text-foreground", sorted && "text-foreground", header.id === "value" && "flex-row-reverse")}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {sorted === "asc" ? <ArrowUpIcon className="size-3.5" /> : sorted === "desc" ? <ArrowDownIcon className="size-3.5" /> : <ChevronsUpDownIcon className="size-3.5 opacity-50" />}
                        </button>
                      ) : (
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                tabIndex={0}
                onClick={() => onOpen(row.original.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault()
                    onOpen(row.original.id)
                  }
                }}
                className={cn("cursor-pointer outline-none focus-visible:bg-muted", isClosed(row.original) && "text-muted-foreground")}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id} className={cn("px-4 py-3", hidden[cell.column.id], (cell.column.id === "value" || cell.column.id === "weighted") && "text-right")}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

const WIDTHS: Record<string, string> = {
  company: "w-[54%] sm:w-[34%] md:w-[26%] lg:w-[22%]",
  stage: "md:w-[14%] lg:w-[12%]",
  value: "w-[25%] sm:w-[16%] md:w-[13%] lg:w-[10%]",
  weighted: "lg:w-[10%]",
  age: "w-[21%] sm:w-[16%] md:w-[13%] lg:w-[10%]",
  next: "",
  contact: "xl:w-[13%]",
}

function sortName(sorting: SortingState) {
  const by = sorting[0]
  if (!by) return "when they were added"
  if (by.id === "value") return by.desc ? "value, largest first" : "value, smallest first"
  if (by.id === "age") return by.desc ? "days in stage, oldest first" : "days in stage, newest first"
  return by.desc ? "next step, latest first" : "next step, soonest first"
}
