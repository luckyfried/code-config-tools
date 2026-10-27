import { useCallback, useEffect, useMemo, useState } from "react"
import { flushSync } from "react-dom"
import { PlusIcon, Settings2Icon } from "lucide-react"
import { Accordion as AccordionPrimitive } from "radix-ui"
import { AddItemDialog } from "@/components/add-item-dialog"
import { Bag } from "@/components/bag"
import { GroupSection } from "@/components/group-section"
import { RollingNumber } from "@/components/rolling-number"
import { SettingsDialog } from "@/components/settings-dialog"
import { TripPicker } from "@/components/trip-picker"
import { WeightBar } from "@/components/weight-bar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useMediaQuery } from "@/hooks/use-media-query"
import { composeList, config, keyOf, usingSample, type AddedItem, type Group } from "@/lib/config"
import { firstPacked, loadTrip, saveTrip, type TripState } from "@/lib/store"
import { cn } from "@/lib/utils"

type Note = { id: number; text: string }

const items = (n: number) => `${n} ${n === 1 ? "item" : "items"}`

/** Splits the groups into columns of about equal height, keeping their order within each column. */
function columnsOf(groups: Group[], count: number): Group[][] {
  const cols: Group[][] = Array.from({ length: count }, () => [])
  const heights = new Array(count).fill(0)
  for (const g of groups) {
    const i = heights.indexOf(Math.min(...heights))
    cols[i].push(g)
    heights[i] += g.items.length + 1.6
  }
  return cols
}

export default function App() {
  const wide = useMediaQuery("(min-width: 768px)")
  const two = useMediaQuery("(min-width: 1100px)")
  const three = useMediaQuery("(min-width: 1600px)")
  const reduce = useMediaQuery("(prefers-reduced-motion: reduce)")

  const [boot] = useState(loadTrip)
  const [trip, setTrip] = useState<TripState>(boot.trip)
  const [risen, setRisen] = useState(false)
  const [note, setNote] = useState<Note | null>(null)
  const [freshKeys, setFreshKeys] = useState<Set<string>>(() => new Set())
  const [tab, setTab] = useState("list")

  const groups = useMemo(() => composeList(trip.templates, trip.added), [trip.templates, trip.added])
  const [open, setOpen] = useState<string[]>(() => groups.map((g) => g.label))
  const allItems = useMemo(() => groups.flatMap((g) => g.items), [groups])
  const packed = useMemo(() => {
    const onList = new Set(allItems.map((i) => i.key))
    return new Set(trip.packed.filter((k) => onList.has(k)))
  }, [allItems, trip.packed])

  const total = allItems.length
  const packedCount = packed.size
  const share = total === 0 ? 0 : packedCount / total
  const shown = risen ? share : 0
  const limit = config.limitKg
  const packedKg = allItems.reduce((s, i) => s + (packed.has(i.key) ? (i.weight ?? 0) : 0), 0)
  const plannedKg = allItems.reduce((s, i) => s + (i.weight ?? 0), 0)
  const left = total - packedCount

  // The bag rises from empty on every visit; the very first visit also checks off what the inputs say is packed.
  useEffect(() => {
    const frame = requestAnimationFrame(() => requestAnimationFrame(() => setRisen(true)))
    if (!boot.fresh || firstPacked.length === 0) return () => cancelAnimationFrame(frame)
    const onList = new Set(composeList(boot.trip.templates, []).flatMap((g) => g.items.map((i) => i.key)))
    const keys = firstPacked.filter((k) => onList.has(k))
    const pack = (k: string) => setTrip((t) => (t.packed.includes(k) ? t : { ...t, packed: [...t.packed, k] }))
    const timers = keys.map((k, i) => setTimeout(() => pack(k), matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 220 + i * 70))
    return () => {
      cancelAnimationFrame(frame)
      timers.forEach(clearTimeout)
    }
  }, [boot])

  useEffect(() => saveTrip(trip), [trip])

  useEffect(() => {
    if (!note) return
    const t = setTimeout(() => setNote(null), 5000)
    return () => clearTimeout(t)
  }, [note])

  useEffect(() => {
    if (freshKeys.size === 0) return
    const t = setTimeout(() => setFreshKeys(new Set()), 600)
    return () => clearTimeout(t)
  }, [freshKeys])

  const toggle = useCallback((key: string) => {
    setTrip((t) => ({
      ...t,
      packed: t.packed.includes(key) ? t.packed.filter((k) => k !== key) : [...t.packed, key],
    }))
  }, [])

  const remove = useCallback((key: string) => {
    setTrip((t) => ({
      ...t,
      added: t.added.filter((a) => keyOf(a.name) !== key),
      packed: t.packed.filter((k) => k !== key),
    }))
  }, [])

  const add = (item: AddedItem) => {
    const key = keyOf(item.name)
    if (allItems.some((i) => i.key === key)) return `${item.name} is already on the list.`
    setTrip((t) => ({ ...t, added: [...t.added, item] }))
    setOpen((o) => (o.includes(item.group) ? o : [...o, item.group]))
    setFreshKeys(new Set([key]))
    return null
  }

  const changeTemplates = (ids: string[]) => {
    const before = new Set(allItems.map((i) => i.key))
    const after = composeList(ids, trip.added).flatMap((g) => g.items.map((i) => i.key))
    const gained = after.filter((k) => !before.has(k)).length
    const lost = before.size - after.filter((k) => before.has(k)).length
    const addedId = ids.find((id) => !trip.templates.includes(id))
    const removedId = trip.templates.find((id) => !ids.includes(id))
    const label = (id?: string) => config.templates.find((t) => t.id === id)?.label ?? "That trip"
    let text = ""
    if (addedId) {
      const size = new Set(
        config.templates.find((t) => t.id === addedId)?.groups.flatMap((g) => g.items.map((i) => keyOf(i.name))) ?? [],
      ).size
      const already = size - gained
      text = `${label(addedId)} added ${items(gained)}${already > 0 ? `; ${already} were already on the list` : ""}.`
    } else if (removedId) {
      text = `${label(removedId)} came off: ${items(lost)} fewer.`
    }
    const apply = () => {
      setTrip((t) => ({ ...t, templates: ids }))
      setOpen((o) => {
        const labels = composeList(ids, trip.added).map((g) => g.label)
        return [...new Set([...o, ...labels.filter((l) => !groups.some((g) => g.label === l))])]
      })
      if (text) setNote({ id: Date.now(), text })
    }
    if (document.startViewTransition && !reduce) document.startViewTransition(() => flushSync(apply))
    else apply()
  }

  const rename = (name: string) => setTrip((t) => ({ ...t, name }))
  const reset = () => setTrip((t) => ({ ...t, packed: [] }))
  const importTrip = (next: TripState) => setTrip(next)

  const composed = trip.templates
    .map((id) => config.templates.find((t) => t.id === id)?.label)
    .filter(Boolean)
    .join(" + ")
  const percent = Math.round(shown * 100)
  const groupLabels = groups.map((g) => g.label)
  const bagLabel = `Bag ${Math.round(share * 100)} percent full: ${packedCount} of ${total} packed`

  const noteLine = note ? (
    <p key={note.id} role="status" className="note-in rounded-xl bg-primary/10 px-4 py-2.5 text-sm font-medium text-pretty text-primary">
      {note.text}
    </p>
  ) : null

  const list =
    total === 0 ? (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed px-6 py-14 text-center">
        <p className="text-lg font-semibold">Nothing on the list yet</p>
        <p className="max-w-xs text-pretty text-muted-foreground">Pick a trip and its things show up here, grouped.</p>
        {!wide ? (
          <Button size="lg" onClick={() => setTab("trips")}>
            Pick a trip
          </Button>
        ) : null}
      </div>
    ) : (
      <AccordionPrimitive.Root
        type="multiple"
        value={open}
        onValueChange={setOpen}
        className={cn(
          "grid items-start gap-3 [view-transition-name:pack-groups] md:gap-4",
          three ? "grid-cols-3" : two ? "grid-cols-2" : "grid-cols-1",
        )}
      >
        {columnsOf(groups, wide ? (three ? 3 : two ? 2 : 1) : 1).map((col, i) => (
          <div key={i} className="flex min-w-0 flex-col gap-3 md:gap-4">
            {col.map((g) => (
              <GroupSection
                key={g.label}
                group={g}
                packed={packed}
                showWeight={limit !== null}
                freshKeys={freshKeys}
                onToggle={toggle}
                onRemove={remove}
              />
            ))}
          </div>
        ))}
      </AccordionPrimitive.Root>
    )

  const settingsButton = (
    <SettingsDialog trip={trip} packedCount={packedCount} onImport={importTrip} onReset={reset}>
      <Button variant="ghost" size="icon" aria-label="Settings">
        <Settings2Icon />
      </Button>
    </SettingsDialog>
  )

  if (!wide) {
    return (
      <Tabs value={tab} onValueChange={setTab} className="min-h-dvh gap-0">
        <header className="no-print sticky top-0 z-20 border-b bg-background pt-[env(safe-area-inset-top)] pr-[env(safe-area-inset-right)] pl-[env(safe-area-inset-left)]">
          <div className="flex items-center gap-4 px-4 pt-3 pb-2">
            <Bag share={shown} label={bagLabel} className="w-[118px] shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[0.9375rem] font-medium">{trip.name || "My trip"}</p>
              <p className="mt-1 flex items-baseline leading-none">
                <RollingNumber value={percent} className="text-[3.25rem] font-semibold tracking-tight" />
                <span className="ml-0.5 text-2xl font-semibold text-muted-foreground">%</span>
              </p>
              <p className="mt-1.5 text-sm text-muted-foreground">
                <span className="font-semibold text-foreground tabular-nums">
                  {packedCount}/{total}
                </span>{" "}
                packed{usingSample ? ", sample trips" : ""}
              </p>
            </div>
            <div className="-mr-1.5 self-start">{settingsButton}</div>
          </div>
          {limit !== null ? (
            <WeightBar packed={packedKg} planned={plannedKg} limit={limit} compact className="px-4 pb-3" />
          ) : null}
          <div className="flex items-center gap-2 px-4 pb-3">
            <TabsList className="flex-1 group-data-horizontal/tabs:h-11">
              <TabsTrigger value="list" className="text-[0.9375rem]">
                List
                <span className="text-muted-foreground tabular-nums">{left > 0 ? `${left} left` : "done"}</span>
              </TabsTrigger>
              <TabsTrigger value="trips" className="text-[0.9375rem]">
                Trips
              </TabsTrigger>
            </TabsList>
            <AddItemDialog groups={groupLabels} showWeight={limit !== null} onAdd={add}>
              <Button size="icon-lg" aria-label="Add an item">
                <PlusIcon className="size-5" />
              </Button>
            </AddItemDialog>
          </div>
        </header>
        <main className="px-3 pt-3 pb-[calc(env(safe-area-inset-bottom)+2rem)]">
          <TabsContent value="list" className="flex flex-col gap-3">
            {noteLine}
            {list}
          </TabsContent>
          <TabsContent value="trips" className="flex flex-col gap-5 px-1 pt-1">
            <div className="flex flex-col gap-2">
              <Label htmlFor="trip-name">Trip name</Label>
              <Input id="trip-name" value={trip.name} onChange={(e) => rename(e.target.value)} autoComplete="off" />
            </div>
            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-medium">Packing for</h2>
              <TripPicker chosen={trip.templates} onChange={changeTemplates} />
            </div>
            {noteLine}
          </TabsContent>
        </main>
      </Tabs>
    )
  }

  return (
    <div className="grid min-h-dvh grid-cols-[minmax(290px,340px)_1fr] lg:grid-cols-[360px_1fr] min-[1600px]:grid-cols-[400px_1fr]">
      <aside className="no-print sticky top-0 flex h-dvh flex-col gap-6 overflow-y-auto border-r border-rail-edge bg-rail px-7 pt-[max(1.75rem,env(safe-area-inset-top))] pb-7 pl-[max(1.75rem,env(safe-area-inset-left))] short:gap-4 short:py-4">
        <div className="flex flex-col gap-1">
          <input
            aria-label="Trip name"
            value={trip.name}
            onChange={(e) => rename(e.target.value)}
            className="-mx-2 rounded-lg bg-transparent px-2 py-1 text-2xl font-semibold text-balance outline-none hover:bg-foreground/5 focus-visible:ring-3 focus-visible:ring-ring/50 short:text-xl"
            autoComplete="off"
          />
          <p className="text-sm text-muted-foreground">
            {composed || "No trip picked"}
            {usingSample ? ", sample trips" : ""}
          </p>
        </div>
        <div className="flex flex-col items-center gap-4 short:flex-row short:items-center short:gap-5">
          <Bag share={shown} label={bagLabel} className="w-full max-w-[268px] min-[1600px]:max-w-[330px] short:w-[132px] short:shrink-0" />
          <div className="flex w-full items-end justify-between short:flex-col short:items-start short:gap-1">
            <p className="flex items-baseline leading-none">
              <RollingNumber value={percent} className="text-[4.5rem] font-semibold tracking-tight short:text-[3.25rem]" />
              <span className="ml-1 text-3xl font-semibold text-muted-foreground short:text-2xl">%</span>
            </p>
            <p className="pb-1.5 text-right text-sm text-muted-foreground short:pb-0 short:text-left">
              <span className="block text-xl font-semibold text-foreground tabular-nums short:inline short:text-sm">
                {packedCount}/{total}
              </span>{" "}
              packed
            </p>
          </div>
        </div>
        {limit !== null ? <WeightBar packed={packedKg} planned={plannedKg} limit={limit} /> : null}
        <div className="flex flex-col gap-2.5">
          <h2 className="small-caps text-[1.0625rem] font-semibold">Trips</h2>
          <TripPicker chosen={trip.templates} onChange={changeTemplates} />
        </div>
      </aside>
      <main className="min-w-0 px-6 pt-[max(1.75rem,env(safe-area-inset-top))] pr-[max(1.5rem,env(safe-area-inset-right))] pb-10 lg:px-10 short:pt-4">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4 short:mb-3">
          <div className="min-w-0">
            <h1 className="text-[1.75rem] leading-tight font-semibold text-balance short:text-xl">
              {total === 0 ? "Pick a trip" : left === 0 ? "Everything's in. Zip it up." : `${items(left)} left to pack`}
            </h1>
            <p className="mt-1 text-muted-foreground tabular-nums">
              {groups.length} groups, {items(total)}
              {limit !== null ? `, ${(Math.round(plannedKg * 10) / 10).toFixed(1)} kg in all` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <AddItemDialog groups={groupLabels} showWeight={limit !== null} onAdd={add}>
              <Button size="lg">
                <PlusIcon data-icon="inline-start" />
                Add item
              </Button>
            </AddItemDialog>
            {settingsButton}
          </div>
        </div>
        {noteLine ? <div className="mb-4">{noteLine}</div> : null}
        {list}
      </main>
    </div>
  )
}
