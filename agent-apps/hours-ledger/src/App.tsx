import { useEffect, useState } from "react"
import { CalendarDaysIcon, ChartColumnStackedIcon, FileTextIcon, SettingsIcon, TimerIcon } from "lucide-react"
import { cn } from "cn"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DayDialog } from "@/components/DayDialog"
import { ManualEntry } from "@/components/ManualEntry"
import { config } from "@/lib/config"
import { running, startTimer, stopTimer, useLedger } from "@/lib/store"
import { MonthView } from "@/views/MonthView"
import { SettingsView } from "@/views/SettingsView"
import { StatementView } from "@/views/StatementView"
import { TodayView } from "@/views/TodayView"
import { WeekView } from "@/views/WeekView"

const SCREENS = [
  { id: "today", label: "Today", icon: TimerIcon },
  { id: "week", label: "Week", icon: ChartColumnStackedIcon },
  { id: "month", label: "Month", icon: CalendarDaysIcon },
  { id: "statement", label: "Statement", icon: FileTextIcon },
  { id: "settings", label: "Settings", icon: SettingsIcon },
] as const
type Screen = (typeof SCREENS)[number]["id"]

function screenFromHash(): Screen {
  const h = window.location.hash.slice(1)
  return (SCREENS.find((s) => s.id === h)?.id ?? "today") as Screen
}

export default function App() {
  const ledger = useLedger()
  const [screen, setScreen] = useState<Screen>(screenFromHash)
  const [adding, setAdding] = useState(false)
  const [day, setDay] = useState<Date | null>(null)

  useEffect(() => {
    const on = () => setScreen(screenFromHash())
    window.addEventListener("hashchange", on)
    return () => window.removeEventListener("hashchange", on)
  }, [])

  const go = (s: Screen) => {
    setScreen(s)
    window.history.replaceState(null, "", s === "today" ? window.location.pathname : `#${s}`)
  }

  // S starts and stops the timer anywhere a text field does not have the keyboard.
  const current = running(ledger)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== "s" || e.metaKey || e.ctrlKey || e.altKey) return
      const t = e.target as HTMLElement
      if (t.closest("input, textarea, select, [contenteditable], [role=dialog]")) return
      e.preventDefault()
      if (current) stopTimer()
      else startTimer(ledger.lastClientId ?? config.clients[0].id)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [current, ledger.lastClientId])

  return (
    <Tabs value={screen} onValueChange={(v) => go(v as Screen)} className="min-h-dvh gap-0">
      <header className="no-print sticky top-0 z-20 border-b bg-background/90 pt-[env(safe-area-inset-top)] backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-full max-w-[1680px] items-center gap-4 px-4 sm:px-6 md:h-16 lg:px-8 short:h-12">
          <div className="flex min-w-0 items-center gap-2.5">
            <Mark />
            <span className="truncate text-base font-semibold tracking-tight">Hours Ledger</span>
          </div>
          <TabsList className="mx-auto hidden h-10 md:inline-flex short:h-9">
            {SCREENS.map((s) => (
              <TabsTrigger key={s.id} value={s.id} className="h-full px-3.5">
                <s.icon data-icon="inline-start" />
                {s.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <span className="ml-auto truncate text-sm text-muted-foreground md:ml-0">{config.name}</span>
        </div>
      </header>

      <main className="print-flat mx-auto w-full max-w-[1680px] px-4 pt-4 pb-[calc(5.5rem+env(safe-area-inset-bottom))] sm:px-6 sm:pt-6 md:pb-10 lg:px-8 short:pt-3">
        <TabsContent value="today">
          <TodayView onAddTime={() => setAdding(true)} onSelectDay={setDay} />
        </TabsContent>
        <TabsContent value="week">
          <WeekView onSelectDay={setDay} />
        </TabsContent>
        <TabsContent value="month">
          <MonthView onSelectDay={setDay} />
        </TabsContent>
        <TabsContent value="statement" className="print-flat">
          <StatementView />
        </TabsContent>
        <TabsContent value="settings">
          <SettingsView />
        </TabsContent>
      </main>

      <nav
        aria-label="Screens"
        className="no-print fixed inset-x-0 bottom-0 z-20 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm md:hidden"
      >
        <div className="grid grid-cols-5">
          {SCREENS.map((s) => (
            <button
              key={s.id}
              type="button"
              aria-current={screen === s.id ? "page" : undefined}
              onClick={() => go(s.id)}
              className={cn(
                "flex h-16 flex-col items-center justify-center gap-1 text-[12px] font-medium transition-colors duration-150",
                screen === s.id ? "text-foreground" : "text-muted-foreground",
              )}
            >
              <s.icon className="size-5" aria-hidden />
              {s.label}
            </button>
          ))}
        </div>
      </nav>

      <ManualEntry open={adding} onOpenChange={setAdding} />
      <DayDialog day={day} onClose={() => setDay(null)} />
    </Tabs>
  )
}

function Mark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden className="shrink-0">
      <rect x="1" y="12" width="5" height="9" rx="1.5" className="fill-chart-3" />
      <rect x="8.5" y="6" width="5" height="15" rx="1.5" className="fill-chart-2" />
      <rect x="16" y="1" width="5" height="20" rx="1.5" className="fill-chart-1" />
    </svg>
  )
}
