import { memo, useEffect, useMemo, useRef, useState } from "react"
import { CheckIcon, ChevronDownIcon } from "lucide-react"
import { Accordion as AccordionPrimitive } from "radix-ui"
import { Bag } from "@/components/bag"
import { ItemRow } from "@/components/item-row"
import { useFlip } from "@/hooks/use-flip"
import type { Group } from "@/lib/config"
import { cn } from "@/lib/utils"

/** How long a checked row stays in place, in ms: the wave's climb and the check stroke, with a beat to read it. */
const SINK_AFTER = 650

type GroupSectionProps = {
  group: Group
  packed: Set<string>
  showWeight: boolean
  freshKeys: Set<string>
  onToggle: (key: string) => void
  onRemove: (key: string) => void
}

/** One group of the list, drawn like the bag: an ink outline, a small bag filling with the group, its count on a
 * luggage tag, a stitch under the header, and its rows, the packed ones sunk to the bottom. */
export const GroupSection = memo(function GroupSection({
  group,
  packed,
  showWeight,
  freshKeys,
  onToggle,
  onRemove,
}: GroupSectionProps) {
  const list = useRef<HTMLUListElement>(null)
  // A checked row sinks once its box has filled: moving it at once would restart it full and hide the climb.
  const [sunk, setSunk] = useState(packed)
  useEffect(() => {
    const wait = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : SINK_AFTER
    const t = setTimeout(() => setSunk(packed), wait)
    return () => clearTimeout(t)
  }, [packed])
  const ordered = useMemo(() => {
    const open = group.items.filter((i) => !sunk.has(i.key))
    const done = group.items.filter((i) => sunk.has(i.key))
    return [...open, ...done]
  }, [group.items, sunk])
  const done = group.items.filter((i) => packed.has(i.key)).length
  const all = done === group.items.length
  useFlip(list, ordered.map((i) => i.key).join("|"))

  return (
    <AccordionPrimitive.Item
      value={group.label}
      className="overflow-hidden rounded-[1.375rem] border-2 border-bag-line bg-card shadow-[0_5px_0_-1px_var(--bag-shadow)]"
    >
      <AccordionPrimitive.Header className="flex">
        <AccordionPrimitive.Trigger className="group/trigger flex min-h-12 flex-1 items-center gap-3 px-4 py-2.5 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:ring-inset">
          <Bag mini share={done / group.items.length} className="-my-1 w-10 shrink-0" />
          <span className="small-caps min-w-0 flex-1 text-[1.0625rem] font-semibold">{group.label}</span>
          <span
            className={cn(
              "luggage-tag relative flex -rotate-3 items-center gap-1 rounded-[7px] border-[1.5px] border-bag-line py-0.5 pr-2 pl-[1.15rem] text-sm font-semibold tabular-nums transition-colors duration-200",
              all ? "bg-primary text-primary-foreground" : "bg-bag-empty text-foreground",
            )}
          >
            {all ? <CheckIcon className="size-3.5" strokeWidth={3} aria-hidden="true" /> : null}
            {done}/{group.items.length}
          </span>
          <ChevronDownIcon
            aria-hidden="true"
            className="size-4 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]/trigger:rotate-180"
          />
        </AccordionPrimitive.Trigger>
      </AccordionPrimitive.Header>
      <AccordionPrimitive.Content className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
        <ul ref={list} className="relative divide-y divide-bag-line/12 border-t-[1.5px] border-dashed border-bag-line/40">
          {ordered.map((item) => (
            <ItemRow
              key={item.key}
              item={item}
              packed={packed.has(item.key)}
              showWeight={showWeight}
              fresh={freshKeys.has(item.key)}
              onToggle={onToggle}
              onRemove={onRemove}
            />
          ))}
        </ul>
      </AccordionPrimitive.Content>
    </AccordionPrimitive.Item>
  )
})
