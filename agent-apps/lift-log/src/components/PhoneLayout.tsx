import { useState } from "react"
import { ChartSplineIcon, ChevronDownIcon, DumbbellIcon, PersonStandingIcon, SlidersHorizontalIcon } from "lucide-react"
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { greeting, statusLine } from "@/lib/greeting"
import { useLog } from "@/lib/log-context"
import { ChartCard } from "./ChartCard"
import { ExercisePicker } from "./ExercisePicker"
import { HistoryList } from "./HistoryList"
import { RestPill } from "./Rest"
import { RecentSessions } from "./RecentSessions"
import { SessionCard } from "./SessionCard"
import { SettingsPanel } from "./SettingsPanel"
import { TodayList } from "./TodayList"
import { MuscleTable, WeekMap } from "./WeekMap"

export type PhoneTab = "session" | "history" | "week" | "settings"

const TABS: { value: PhoneTab; label: string; icon: typeof DumbbellIcon }[] = [
  { value: "session", label: "Session", icon: DumbbellIcon },
  { value: "history", label: "History", icon: ChartSplineIcon },
  { value: "week", label: "Week", icon: PersonStandingIcon },
  { value: "settings", label: "Settings", icon: SlidersHorizontalIcon },
]

function Title({ children, sub }: { children: React.ReactNode; sub?: string }) {
  return (
    <div className="min-w-0">
      <h1 className="truncate text-xl font-semibold tracking-tight text-balance">{children}</h1>
      {sub ? <p className="text-sm text-pretty text-muted-foreground">{sub}</p> : null}
    </div>
  )
}

/** One column, the tabs at the thumb, the steppers within reach. */
export function PhoneLayout({ tab, onTab }: { tab: PhoneTab; onTab: (t: PhoneTab) => void }) {
  const log = useLog()
  const [picking, setPicking] = useState(false)

  return (
    <Tabs value={tab} onValueChange={(v) => onTab(v as PhoneTab)} className="min-h-dvh gap-0">
      <main className="mx-auto flex w-full max-w-[1023px] flex-1 flex-col px-4 pt-[calc(env(safe-area-inset-top)+16px)] pb-[calc(env(safe-area-inset-bottom)+92px)] sm:px-6 short:max-w-none short:pt-[calc(env(safe-area-inset-top)+12px)] short:pr-[calc(env(safe-area-inset-right)+16px)] short:pb-[calc(env(safe-area-inset-bottom)+16px)] short:pl-[calc(env(safe-area-inset-left)+104px)]">
        <TabsContent value="session" className="flex flex-col gap-3">
          <header className="flex min-h-11 items-center justify-between gap-3 short:hidden">
            <Title sub={statusLine(log.sample)}>{greeting(log.config.name)}</Title>
            <RestPill />
          </header>
          <div className="grid gap-3 md:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] md:items-start short:grid-cols-1">
            <SessionCard onPickExercise={() => setPicking(true)} />
            <div className="flex flex-col gap-3 short:grid short:grid-cols-2 short:items-start">
              <header className="hidden min-h-11 items-center justify-between gap-3 short:col-span-2 short:flex">
                <Title sub={statusLine(log.sample)}>{greeting(log.config.name)}</Title>
                <RestPill />
              </header>
              <WeekMap layout="row" onOpen={() => onTab("week")} />
              <TodayList className="max-md:hidden short:flex" />
            </div>
          </div>
          <TodayList className="md:hidden short:hidden" />
          <RecentSessions count={4} />
        </TabsContent>

        <TabsContent value="history" className="flex flex-col gap-3">
          <header className="flex min-h-11 items-center justify-between gap-3">
            <Title sub="Every set, and the curve it draws">History</Title>
            <RestPill />
          </header>
          <button
            type="button"
            onClick={() => setPicking(true)}
            className="press surface flex min-h-12 items-center justify-between rounded-xl px-4 text-left hover:bg-accent"
            aria-label={`${log.selected.label}. Choose another lift`}
          >
            <span className="font-medium">{log.selected.label}</span>
            <ChevronDownIcon className="size-5 text-muted-foreground" />
          </button>
          <div className="grid gap-3 md:grid-cols-2 md:items-start">
            <ChartCard height={230} />
            <HistoryList />
          </div>
        </TabsContent>

        <TabsContent value="week" className="flex flex-col gap-3">
          <header className="flex min-h-11 items-center justify-between gap-3">
            <Title sub="Today and the six days before">This week</Title>
            <RestPill />
          </header>
          <div className="grid gap-3 md:grid-cols-2 md:items-start">
            <WeekMap layout="stack" interactive />
            <MuscleTable />
          </div>
        </TabsContent>

        <TabsContent value="settings" className="flex flex-col gap-3">
          <header className="flex min-h-11 items-center justify-between gap-3">
            <Title>Settings</Title>
            <RestPill />
          </header>
          <SettingsPanel className="md:max-w-2xl" />
        </TabsContent>
      </main>

      <nav
        className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t bg-background/92 backdrop-blur-md short:inset-x-auto short:top-0 short:left-0 short:flex short:w-[calc(env(safe-area-inset-left)+88px)] short:items-center short:border-t-0 short:border-r short:pl-[env(safe-area-inset-left)]"
        aria-label="Screens"
      >
        <TabsList className="mx-auto grid w-full max-w-lg grid-cols-4 rounded-none bg-transparent p-1.5 group-data-horizontal/tabs:h-auto short:grid-cols-1 short:gap-1">
          {TABS.map(({ value, label, icon: Icon }) => (
            <TabsTrigger key={value} value={value} className="h-14 flex-col gap-1 rounded-xl text-xs data-active:bg-secondary dark:data-active:border-transparent dark:data-active:bg-secondary short:h-16">
              <Icon className="size-5" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>
      </nav>

      <Drawer open={picking} onOpenChange={setPicking}>
        <DrawerContent className="max-h-[88dvh]">
          <DrawerHeader className="pb-1 text-left">
            <DrawerTitle>Choose a lift</DrawerTitle>
            <DrawerDescription>Today's lifts come first.</DrawerDescription>
          </DrawerHeader>
          <div className="safe-bottom flex min-h-0 flex-1 flex-col px-3 pb-3">
            <ExercisePicker onPicked={() => setPicking(false)} listClassName="max-h-[62dvh]" />
          </div>
        </DrawerContent>
      </Drawer>
    </Tabs>
  )
}
