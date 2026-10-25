import { useEffect, useMemo, useRef, useState } from "react"
import { format } from "date-fns"
import { CalendarDays, ChevronLeft, House, Plus, Settings2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { AnimatedNumber } from "@/components/AnimatedNumber"
import { FoodDrawer, type DrawerState } from "@/components/FoodDrawer"
import { Library } from "@/components/Library"
import { MacroLegend } from "@/components/MacroLegend"
import { MealList } from "@/components/MealList"
import { QuickTray } from "@/components/QuickTray"
import { Rings, type RingKey, type RingsHandle } from "@/components/Rings"
import { SettingsPanel } from "@/components/SettingsPanel"
import { WaterCounter } from "@/components/WaterCounter"
import { WeekPanel } from "@/components/WeekPanel"
import { useMedia } from "@/hooks/useMedia"
import { readConfig, type Food, type Macros } from "@/lib/config"
import { dayKey, fmt, mealAt, parseDay, totals, trayOrder, type Entry } from "@/lib/nutrition"
import { prefersReducedMotion } from "@/lib/motion"
import { useSaved } from "@/lib/store"
import { cn } from "@/lib/utils"

const config = readConfig()

type Tab = "today" | "add" | "week" | "settings"

const TABS: { id: Tab; label: string; icon: typeof House }[] = [
  { id: "today", label: "Today", icon: House },
  { id: "add", label: "Add", icon: Plus },
  { id: "week", label: "Week", icon: CalendarDays },
  { id: "settings", label: "Settings", icon: Settings2 },
]

function greeting(now: Date, name: string) {
  const h = now.getHours()
  const part = h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"
  return name.trim() ? `${part}, ${name.trim()}` : part
}

/** Today's log in the order it was eaten: by meal, then by the time each entry was logged. */
const servingOrder = (list: Entry[], meals: string[]) =>
  list.toSorted((a, b) => {
    const ma = meals.indexOf(a.meal)
    const mb = meals.indexOf(b.meal)
    return (ma < 0 ? meals.length : ma) - (mb < 0 ? meals.length : mb) || a.at - b.at
  })

const ratios = (t: Macros, target: Macros) => ({
  calories: t.calories / target.calories,
  protein: t.protein / target.protein,
  carbs: t.carbs / target.carbs,
  fat: t.fat / target.fat,
})

export default function App() {
  const store = useSaved(config)
  const { saved } = store
  const wide = useMedia("(min-width: 1024px)")
  const [tab, setTab] = useState<Tab>("today")
  const [now] = useState(() => new Date())
  const today = dayKey(now)
  const [viewing, setViewing] = useState(today)
  const [drawer, setDrawer] = useState<DrawerState | null>(null)
  /*
   * The opening: today's log is served again in the order it was eaten. Each entry slides into its meal, the rings
   * and the calories left follow it, and the ring that moved most pulses once the last one lands.
   */
  const [opening, setOpening] = useState<string[] | null>(() => {
    const list = saved.days[today] ?? []
    return prefersReducedMotion() || !list.length ? null : servingOrder(list, config.meals).map((e) => e.id)
  })
  const [served, setServed] = useState(0)
  const [fresh, setFresh] = useState<Set<string>>(() => new Set(opening ?? []))
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [pendingMeal, setPendingMeal] = useState<string | null>(null)
  const rings = useRef<RingsHandle>(null)

  const targets = saved.targets ?? config.targets
  const allFoods = useMemo(() => [...config.foods, ...saved.foods.filter((f) => !config.foods.some((c) => c.id === f.id))], [saved.foods])
  const foodMap = useMemo(() => new Map(allFoods.map((f) => [f.id, f])), [allFoods])
  const logged = saved.days[viewing] ?? []
  const servedIds = useMemo(() => (opening ? new Set(opening.slice(0, served)) : null), [opening, served])
  const entries = servedIds && viewing === today ? logged.filter((e) => servedIds.has(e.id)) : logged
  const eaten = totals(entries, foodMap)
  /* Eaten and left are both shown, so each is a whole number and together they make the target. */
  const eatenKcal = Math.round(eaten.calories)
  const left = Math.round(targets.calories) - eatenKcal

  const counts = useMemo(() => {
    const m = new Map<string, number>()
    for (const list of Object.values(saved.days)) for (const e of list) m.set(e.foodId, (m.get(e.foodId) ?? 0) + 1)
    return m
  }, [saved.days])
  const tray = useMemo(() => trayOrder(allFoods, now, counts), [allFoods, now, counts])
  const takenIds = useMemo(() => new Set(allFoods.map((f) => f.id)), [allFoods])

  useEffect(() => {
    if (!opening) return
    let live = true
    let timer = 0
    const step = Math.min(200, 1200 / opening.length)
    const serve = (n: number) => {
      if (!live) return
      setServed(n)
      if (n < opening.length) timer = window.setTimeout(() => serve(n + 1), step)
      else {
        const all = totals(saved.days[today] ?? [], foodMap)
        const r = ratios(all, targets)
        const keys: RingKey[] = ["protein", "carbs", "fat"]
        rings.current?.pulse(keys.reduce((best, k) => (r[k] > r[best] ? k : best), keys[0]))
        timer = window.setTimeout(() => live && setOpening(null), 1200)
      }
    }
    /* The first entry is served once the type is in, so the count never jumps between two fonts. */
    void document.fonts.ready.then(() => {
      if (live) timer = window.setTimeout(() => serve(1), 120)
    })
    return () => {
      live = false
      window.clearTimeout(timer)
    }
    // The opening runs once, on the log the page opened with.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const openAdd = (food: Food, meal = mealAt(config.meals, now)) => setDrawer({ mode: "add", food, servings: 1, meal })

  /** The ring whose share of its target changes the most is the one that pulses. */
  const pulseFor = (before: Entry[], after: Entry[]) => {
    const a = ratios(totals(before, foodMap), targets)
    const b = ratios(totals(after, foodMap), targets)
    const keys: RingKey[] = ["protein", "carbs", "fat"]
    const top = keys.reduce((best, k) => (Math.abs(b[k] - a[k]) > Math.abs(b[best] - a[best]) ? k : best), keys[0])
    if (Math.abs(b[top] - a[top]) > 0.001) rings.current?.pulse(top)
  }

  const confirm = (servings: number, meal: string) => {
    if (!drawer) return
    setOpening(null)
    const before = logged
    let after: Entry[]
    if (drawer.mode === "add") {
      const id = store.add(viewing, drawer.food.id, servings, meal)
      after = [...before, { id, foodId: drawer.food.id, servings, meal, at: Date.now() }]
      setFresh((s) => new Set(s).add(id))
    } else {
      store.update(viewing, drawer.entryId, { servings, meal })
      after = before.map((e) => (e.id === drawer.entryId ? { ...e, servings, meal } : e))
    }
    pulseFor(before, after)
    setDrawer(null)
    if (!wide && drawer.mode === "add") setTab("today")
  }

  const removeEntry = () => {
    if (drawer?.mode !== "edit") return
    setOpening(null)
    store.remove(viewing, drawer.entryId)
    setDrawer(null)
  }

  const pickDay = (key: string) => {
    setOpening(null)
    setViewing(key)
    if (!wide) setTab("today")
  }

  const isToday = viewing === today
  const viewDate = parseDay(viewing)

  const header = (
    <header className="flex flex-col gap-1">
      {isToday ? (
        <p className="text-sm text-muted-foreground">{greeting(now, config.name)}</p>
      ) : (
        <button
          type="button"
          onClick={() => setViewing(today)}
          className="-ml-1 flex h-8 items-center gap-0.5 self-start rounded-md pr-2 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
          Back to today
        </button>
      )}
      <h1 className="text-lg font-semibold">{format(viewDate, "EEEE, MMMM d")}</h1>
      <p className="flex items-baseline gap-2" aria-live="polite">
        <AnimatedNumber
          value={Math.abs(left)}
          from={isToday ? targets.calories : undefined}
          className={cn("text-hero font-semibold tracking-tight tabular-nums", left < 0 && "text-energy-deep")}
        />
        <span className="text-sm text-muted-foreground">{left < 0 ? "kcal over" : isToday ? "kcal left today" : "kcal left that day"}</span>
      </p>
    </header>
  )

  const ringBlock = (
    <div className="flex flex-col items-center gap-5 lg:flex-1 lg:justify-center lg:gap-8">
      <Rings
        handle={rings}
        className="w-[min(74vw,18.5rem)] shrink-0 lg:w-[min(100%,calc(100dvh-30.5rem))]"
        values={ratios(eaten, targets)}
        label={`${fmt(eatenKcal)} of ${fmt(targets.calories)} kcal, ${fmt(eaten.protein)} g protein, ${fmt(eaten.carbs)} g carbs, ${fmt(eaten.fat)} g fat`}
      >
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <AnimatedNumber value={eatenKcal} from={0} className="text-lg leading-tight font-semibold tabular-nums" />
          <span className="text-xs text-muted-foreground tabular-nums">of {fmt(targets.calories)}</span>
        </div>
      </Rings>
      <MacroLegend eaten={eaten} targets={targets} className="w-full min-w-0" />
    </div>
  )

  const water = config.water && (
    <section aria-label="Water" className="surface rounded-xl px-3 pt-2.5 pb-2">
      <WaterCounter count={saved.water[viewing] ?? 0} onChange={(n) => store.setWater(viewing, n)} />
    </section>
  )

  const meals = (
    <MealList
      meals={config.meals}
      entries={entries}
      foods={foodMap}
      fresh={fresh}
      dense={wide}
      onEdit={(e, f) => setDrawer({ mode: "edit", food: f, servings: e.servings, meal: e.meal, entryId: e.id })}
      onAdd={(meal) => {
        if (wide) document.getElementById("library-search")?.focus()
        else setTab("add")
        setPendingMeal(meal)
      }}
    />
  )

  const pick = (f: Food) => {
    openAdd(f, pendingMeal ?? undefined)
    setPendingMeal(null)
  }

  const settings = (
    <SettingsPanel saved={saved} targets={targets} startTargets={config.targets} onTargets={store.setTargets} onReplace={store.replace} />
  )

  const week = (
    <WeekPanel
      today={today}
      viewing={viewing}
      days={saved.days}
      foods={foodMap}
      targets={targets}
      onPick={pickDay}
      delay={wide ? 450 : 0}
      layout={wide ? "wide" : "stack"}
      title={
        <h2 id="week-h" className="text-lg font-semibold">
          This week
        </h2>
      }
    />
  )

  const library = <Library foods={allFoods} onPick={pick} onSave={store.addFood} takenIds={takenIds} searchOnly={wide} />

  const drawerEl = <FoodDrawer state={drawer} meals={config.meals} onClose={() => setDrawer(null)} onConfirm={confirm} onRemove={removeEntry} />

  if (wide) {
    return (
      <div className="mx-auto flex h-dvh min-h-[50rem] max-w-[90rem] flex-col gap-5 px-8 py-5">
        <div className="flex items-center gap-3">
          <Logo />
          <span className="text-lg font-semibold">Plate Log</span>
          <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="ml-auto h-10">
                <Settings2 data-icon="inline-start" />
                Settings
              </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>Settings</DialogTitle>
                <DialogDescription>Your targets and your log.</DialogDescription>
              </DialogHeader>
              {settings}
            </DialogContent>
          </Dialog>
        </div>
        <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] gap-5">
          <section aria-label="Today" className="surface row-span-2 flex min-h-0 flex-col gap-6 rounded-2xl p-7">
            {header}
            {ringBlock}
            {water}
          </section>
          <section aria-labelledby="week-h" className="surface col-span-2 rounded-2xl px-6 py-5">
            {week}
          </section>
          <section aria-labelledby="meals-h" className="surface flex min-h-0 flex-col gap-3 overflow-y-auto rounded-2xl px-6 py-5">
            <h2 id="meals-h" className="text-lg font-semibold">
              {isToday ? "Today's meals" : `Meals on ${format(viewDate, "EEEE")}`}
            </h2>
            {meals}
          </section>
          <section aria-labelledby="lib-h" className="surface flex min-h-0 flex-col gap-4 overflow-y-auto rounded-2xl px-6 py-5">
            <h2 id="lib-h" className="text-lg font-semibold">
              {pendingMeal ? `Add to ${pendingMeal}` : "Your foods"}
            </h2>
            <QuickTray foods={tray.slice(0, 6)} onPick={pick} layout="grid" />
            {library}
          </section>
        </main>
        {drawerEl}
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <main className={cn("flex flex-1 flex-col gap-5 px-4 pt-[max(1rem,env(safe-area-inset-top))]", tab === "today" ? "pb-60" : "pb-28")}>
        {tab === "today" && (
          <>
            {header}
            {ringBlock}
            {water}
            {meals}
          </>
        )}
        {tab === "add" && (
          <>
            <h1 className="text-title font-semibold">{pendingMeal ? `Add to ${pendingMeal}` : "Add food"}</h1>
            {library}
          </>
        )}
        {tab === "week" && (
          <>
            <h1 className="text-title font-semibold">This week</h1>
            {week}
          </>
        )}
        {tab === "settings" && (
          <>
            <h1 className="text-title font-semibold">Settings</h1>
            {settings}
          </>
        )}
      </main>

      <div className="fixed inset-x-0 bottom-0 z-40 flex flex-col border-t bg-background/90 backdrop-blur-md">
        {tab === "today" && (
          <div className="pt-2.5">
            <p className="px-4 pb-1.5 text-xs font-medium text-muted-foreground">Quick add</p>
            <QuickTray foods={tray} onPick={pick} layout="row" />
          </div>
        )}
        <nav aria-label="Screens" className="grid grid-cols-4 pb-[env(safe-area-inset-bottom)]">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={cn(
                "flex h-16 flex-col items-center justify-center gap-1 text-xs outline-none transition-colors focus-visible:bg-muted",
                tab === t.id ? "font-semibold text-foreground" : "text-muted-foreground",
              )}
            >
              <t.icon className="size-5" aria-hidden="true" />
              {t.label}
            </button>
          ))}
        </nav>
      </div>
      {drawerEl}
    </div>
  )
}

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
      <circle cx="16" cy="16" r="13" fill="none" className="stroke-protein" strokeWidth="4" strokeLinecap="round" strokeDasharray="60 82" transform="rotate(-90 16 16)" />
      <circle cx="16" cy="16" r="7.5" fill="none" className="stroke-carbs" strokeWidth="4" strokeLinecap="round" strokeDasharray="34 48" transform="rotate(-90 16 16)" />
      <circle cx="16" cy="16" r="2.5" className="fill-fat" />
    </svg>
  )
}
