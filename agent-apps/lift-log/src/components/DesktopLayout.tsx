import { SlidersHorizontalIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
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

/** Three panes: the week and the lifts, the session, and the selected lift's curve. */
export function DesktopLayout() {
  const log = useLog()
  return (
    <div className="grid h-dvh grid-cols-[minmax(320px,390px)_minmax(0,1fr)_minmax(0,1fr)] gap-5 p-5 2xl:gap-6 2xl:p-6">
      <aside className="flex min-h-0 flex-col gap-4" aria-label="This week and your lifts">
        <WeekMap layout="stack" interactive className="shrink-0" />
        <Tabs defaultValue="lifts" className="surface min-h-0 flex-1 gap-0 overflow-hidden rounded-2xl">
          <TabsList className="m-2 mb-0 grid w-auto grid-cols-2 group-data-horizontal/tabs:h-10">
            <TabsTrigger value="lifts">Lifts</TabsTrigger>
            <TabsTrigger value="muscles">Muscles</TabsTrigger>
          </TabsList>
          <TabsContent value="lifts" className="flex min-h-0 flex-1 flex-col p-2">
            <ExercisePicker className="min-h-0 flex-1" listClassName="pane-scroll min-h-0 flex-1" />
          </TabsContent>
          <TabsContent value="muscles" className="pane-scroll min-h-0 flex-1 overflow-y-auto px-2 pt-2">
            <MuscleTable />
          </TabsContent>
        </Tabs>
      </aside>

      <main className="pane-scroll -mx-2 flex min-h-0 flex-col gap-4 overflow-y-auto px-2 *:shrink-0">
        <header className="flex min-h-11 items-center justify-between gap-3 pt-1">
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-semibold tracking-tight">{greeting(log.config.name)}</h1>
            <p className="text-sm text-pretty text-muted-foreground">{statusLine(log.sample)}</p>
          </div>
          <div className="flex items-center gap-2">
            <RestPill />
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="icon" className="size-11" aria-label="Settings">
                  <SlidersHorizontalIcon className="size-5" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-xl">
                <DialogHeader>
                  <DialogTitle>Settings</DialogTitle>
                  <DialogDescription>Units, rest, and your log.</DialogDescription>
                </DialogHeader>
                <SettingsPanel className="px-0 shadow-none" />
              </DialogContent>
            </Dialog>
          </div>
        </header>
        <SessionCard size="lg" />
        <TodayList />
        <RecentSessions />
      </main>

      <aside className="pane-scroll -mx-2 flex min-h-0 flex-col gap-4 overflow-y-auto px-2 *:shrink-0" aria-label={`${log.selected.label} history`}>
        <ChartCard height={330} />
        <HistoryList />
      </aside>
    </div>
  )
}
