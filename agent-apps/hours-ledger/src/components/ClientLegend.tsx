import { clientColor, config } from "@/lib/config"

export function ClientLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {config.clients.map((c) => (
        <li key={c.id} className="flex items-center gap-1.5" style={{ "--c": clientColor(c.id) } as React.CSSProperties}>
          <span className="size-2.5 rounded-[3px] bg-(--c)" aria-hidden />
          {c.name}
        </li>
      ))}
    </ul>
  )
}
