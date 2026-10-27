import * as React from "react"
import { cn } from "@/lib/utils"
import { Checkbox as CheckboxPrimitive } from "radix-ui"
import { WaveMark } from "@/components/wave-mark"

/** Checking fills the box the way the bag fills: the wave climbs in, then the check stroke draws over it. */
function Checkbox({
  className,
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "peer relative grid size-6 shrink-0 place-items-center rounded-[7px] outline-none after:absolute after:-inset-3 focus-visible:ring-3 focus-visible:ring-ring/50 active:scale-90 transition-transform duration-150 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      <WaveMark on={props.checked === true} />
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
