import { format, parseISO } from "date-fns"
import { CalendarIcon, CheckIcon, Trash2Icon, XIcon } from "lucide-react"
import { useState } from "react"
import { AgeRing } from "@/components/AgeRing"
import { CompanyMark } from "@/components/CompanyMark"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { config } from "@/config"
import { WIDE, useMedia } from "@/hooks/use-media"
import { dayLabel, money, when } from "@/lib/format"
import { LOST, WON, daysInStage, isClosed, type Deal, type Stage } from "@/lib/pipeline"

type Draft = Pick<Deal, "company" | "value" | "stage" | "contact" | "nextStep" | "date" | "notes">

export interface DealSheetProps {
  /** A deal to show, "new" for a blank one, or null when the sheet is closed. */
  deal: Deal | "new" | null
  stages: Stage[]
  defaultStage: string
  now: number
  onClose: () => void
  onCreate: (draft: Draft) => void
  onChange: (id: string, change: Partial<Draft>) => void
  onStage: (id: string, to: string) => void
  onDelete: (id: string) => void
}

const label = (stages: Stage[], id: string) => (id === WON ? "Won" : id === LOST ? "Lost" : stages.find((s) => s.id === id)?.label ?? id)

export function DealSheet(props: DealSheetProps) {
  const wide = useMedia(WIDE)
  const { deal } = props
  return (
    <Sheet open={deal !== null} onOpenChange={(open) => !open && props.onClose()}>
      <SheetContent
        side={wide ? "right" : "bottom"}
        onOpenAutoFocus={(event) => {
          // A new deal starts in the company field on a wide screen; an open deal, or any deal on a phone, waits for a tap.
          if (deal !== "new" || !wide) event.preventDefault()
        }}
        className={wide ? "w-full gap-0 sm:max-w-md" : "max-h-[92dvh] gap-0 rounded-t-3xl pb-[env(safe-area-inset-bottom)]"}
      >
        {deal === null ? null : <SheetBody key={deal === "new" ? "new" : deal.id} {...props} deal={deal} />}
      </SheetContent>
    </Sheet>
  )
}

function SheetBody({ deal, stages, defaultStage, now, onCreate, onChange, onStage, onDelete, onClose }: DealSheetProps & { deal: Deal | "new" }) {
  const creating = deal === "new"
  const [draft, setDraft] = useState<Draft>(() =>
    creating ? { company: "", value: 0, stage: defaultStage, contact: "", nextStep: "", date: "", notes: "" } : { ...deal },
  )
  const [valueText, setValueText] = useState(() => (creating || !deal.value ? "" : String(deal.value)))
  const [tried, setTried] = useState(false)
  const stage = creating ? draft.stage : deal.stage

  const edit = (change: Partial<Draft>) => {
    setDraft((current) => ({ ...current, ...change }))
    if (!creating) onChange(deal.id, change)
  }
  const missing = draft.company.trim() === ""
  const probability = stages.find((s) => s.id === stage)?.probability

  return (
    <>
      <SheetHeader className="border-b px-5 pt-5 pb-4">
        <div className="flex items-center gap-3 pr-8">
          <CompanyMark company={draft.company} className="size-11 text-lg" />
          <div className="min-w-0">
            <SheetTitle className="truncate text-lg">{creating ? "New deal" : draft.company || "Untitled deal"}</SheetTitle>
            <SheetDescription className="tabular-nums">
              {creating
                ? "Add it to the board."
                : isClosed(deal)
                  ? `${label(stages, deal.stage)} ${when(deal.enteredAt, now)}, ${money(deal.value)}`
                  : `${money((deal.value * (probability ?? 0)) / 100)} weighted at ${probability}%`}
            </SheetDescription>
          </div>
        </div>
      </SheetHeader>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        <FieldGroup className="gap-5">
          <Field data-invalid={tried && missing ? true : undefined}>
            <FieldLabel htmlFor="deal-company">Company</FieldLabel>
            <Input id="deal-company" value={draft.company} autoComplete="organization" aria-invalid={tried && missing} onChange={(e) => edit({ company: e.target.value })} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field>
              <FieldLabel htmlFor="deal-value">Value ({config.currency})</FieldLabel>
              <Input
                id="deal-value"
                inputMode="numeric"
                className="tabular-nums"
                value={valueText}
                placeholder="0"
                onChange={(e) => {
                  const digits = e.target.value.replace(/[^\d]/g, "")
                  setValueText(digits)
                  edit({ value: digits === "" ? 0 : Number(digits) })
                }}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="deal-stage">Stage</FieldLabel>
              <Select
                value={stage}
                onValueChange={(to) => {
                  if (creating) setDraft((current) => ({ ...current, stage: to }))
                  else onStage(deal.id, to)
                }}
              >
                <SelectTrigger id="deal-stage" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent position="popper">
                  <SelectGroup>
                    <SelectLabel>Open</SelectLabel>
                    {stages.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        <span data-stage="" style={{ "--stage-raw": s.color } as React.CSSProperties} className="size-2 rounded-full bg-stage" />
                        {s.label}
                        <span className="text-muted-foreground tabular-nums">{s.probability}%</span>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                  {creating ? null : (
                    <SelectGroup>
                      <SelectLabel>Closed</SelectLabel>
                      <SelectItem value={WON}>
                        <span className="size-2 rounded-full bg-won" />
                        Won
                      </SelectItem>
                      <SelectItem value={LOST}>
                        <span className="size-2 rounded-full bg-lost" />
                        Lost
                      </SelectItem>
                    </SelectGroup>
                  )}
                </SelectContent>
              </Select>
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="deal-contact">Contact</FieldLabel>
            <Input id="deal-contact" value={draft.contact} autoComplete="name" onChange={(e) => edit({ contact: e.target.value })} />
          </Field>
          <div className="grid grid-cols-[1fr_auto] items-end gap-3">
            <Field>
              <FieldLabel htmlFor="deal-next">Next step</FieldLabel>
              <Input id="deal-next" value={draft.nextStep} placeholder="Send the proposal" onChange={(e) => edit({ nextStep: e.target.value })} />
            </Field>
            <Field>
              <FieldLabel htmlFor="deal-date">By</FieldLabel>
              <Popover>
                <PopoverTrigger asChild>
                  <Button id="deal-date" variant="outline" className="justify-start font-normal tabular-nums">
                    <CalendarIcon data-icon="inline-start" />
                    {draft.date ? dayLabel(draft.date) : "Pick a date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="end">
                  <Calendar
                    mode="single"
                    selected={draft.date ? parseISO(draft.date) : undefined}
                    defaultMonth={draft.date ? parseISO(draft.date) : undefined}
                    onSelect={(day) => edit({ date: day ? format(day, "yyyy-MM-dd") : "" })}
                  />
                  {draft.date ? (
                    <div className="border-t p-2">
                      <Button variant="ghost" size="sm" className="w-full" onClick={() => edit({ date: "" })}>
                        Clear the date
                      </Button>
                    </div>
                  ) : null}
                </PopoverContent>
              </Popover>
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="deal-notes">Notes</FieldLabel>
            <Textarea id="deal-notes" value={draft.notes} rows={3} onChange={(e) => edit({ notes: e.target.value })} />
          </Field>
        </FieldGroup>

        {creating ? null : (
          <>
            <Separator className="my-6" />
            <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
              Stage moves
              {isClosed(deal) ? null : (
                <span className="ml-auto flex items-center gap-1.5 text-[13px] font-normal text-muted-foreground tabular-nums">
                  <AgeRing days={daysInStage(deal, now)} />
                  {daysInStage(deal, now)} days in {label(stages, deal.stage)}
                </span>
              )}
            </h3>
            <ol className="flex flex-col">
              {[...deal.log].reverse().map((move, i) => (
                <li key={`${move.at}-${i}`} className="relative flex items-baseline gap-3 pb-3 pl-5 text-sm last:pb-0">
                  <span className="absolute top-[0.4rem] left-0 size-2 rounded-full bg-foreground/30" />
                  {i < deal.log.length - 1 ? <span className="absolute top-4 bottom-0 left-[3.5px] w-px bg-border" /> : null}
                  <span className="text-pretty">
                    {move.from === null ? `Added in ${label(stages, move.to)}` : move.to === WON ? "Won" : move.to === LOST ? `Lost at ${label(stages, move.from)}` : `${label(stages, move.from)} to ${label(stages, move.to)}`}
                  </span>
                  <span className="ml-auto shrink-0 text-[13px] text-muted-foreground">{when(move.at, now)}</span>
                </li>
              ))}
            </ol>
          </>
        )}
      </div>

      <SheetFooter className="flex-row flex-wrap gap-2 border-t px-5 py-4">
        {creating ? (
          <Button
            size="lg"
            className="flex-1"
            onClick={() => {
              setTried(true)
              if (!missing) onCreate({ ...draft, company: draft.company.trim() })
            }}
          >
            Add deal
          </Button>
        ) : (
          <>
            {isClosed(deal) ? null : (
              <>
                <Button size="lg" className="flex-1" onClick={() => onStage(deal.id, WON)}>
                  <CheckIcon data-icon="inline-start" />
                  Mark won
                </Button>
                <Button size="lg" variant="outline" className="flex-1" onClick={() => onStage(deal.id, LOST)}>
                  <XIcon data-icon="inline-start" />
                  Mark lost
                </Button>
              </>
            )}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="icon-lg" variant="ghost" aria-label="Delete this deal">
                  <Trash2Icon />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete {deal.company}?</AlertDialogTitle>
                  <AlertDialogDescription>The deal and its stage moves leave the board for good. Mark it lost instead to keep it in the Lost drawer.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep it</AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={() => {
                      onDelete(deal.id)
                      onClose()
                    }}
                  >
                    Delete deal
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        )}
      </SheetFooter>
    </>
  )
}
