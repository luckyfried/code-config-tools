import { cn } from "cn"

// A titled surface: the heading and its figure on one line, the content below; order sets its place in the load.
export function Panel({
  title,
  figure,
  action,
  order = 1,
  className,
  children,
}: {
  title: React.ReactNode
  figure?: React.ReactNode
  action?: React.ReactNode
  order?: number
  className?: string
  children: React.ReactNode
}) {
  return (
    <section
      className={cn("surface arrive flex flex-col gap-4 rounded-2xl p-5 text-card-foreground sm:p-6", className)}
      style={{ "--i": order } as React.CSSProperties}
    >
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-base font-semibold text-balance">{title}</h2>
        {figure ? <span className="font-mono text-sm text-muted-foreground tnum">{figure}</span> : null}
        {action ? <div className="ml-auto flex items-center gap-1">{action}</div> : null}
      </header>
      {children}
    </section>
  )
}
