import type { ReactNode } from "react"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog"
import { Drawer, DrawerContent, DrawerDescription, DrawerTitle } from "@/components/ui/drawer"
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet"

/** A drawer from the bottom on a phone; a centered page or a side sheet on a larger screen. */
export function Panel({
  open,
  onOpenChange,
  phone,
  kind,
  title,
  description,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  phone: boolean
  kind: "page" | "side"
  title: string
  description: string
  children: ReactNode
}) {
  if (phone) {
    return (
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent className="max-h-[92dvh] bg-background pb-[env(safe-area-inset-bottom)]">
          <DrawerTitle className="sr-only">{title}</DrawerTitle>
          <DrawerDescription className="sr-only">{description}</DrawerDescription>
          <div className="overflow-y-auto overscroll-contain px-5 pt-3 pb-6">{children}</div>
        </DrawerContent>
      </Drawer>
    )
  }
  if (kind === "side") {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-[460px] gap-0 bg-background p-0 sm:max-w-[460px]">
          <SheetTitle className="sr-only">{title}</SheetTitle>
          <SheetDescription className="sr-only">{description}</SheetDescription>
          <div className="overflow-y-auto px-7 pt-8 pb-10">{children}</div>
        </SheetContent>
      </Sheet>
    )
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88dvh] gap-0 overflow-y-auto rounded-sm bg-background p-0 sm:max-w-[760px]">
        <DialogTitle className="sr-only">{title}</DialogTitle>
        <DialogDescription className="sr-only">{description}</DialogDescription>
        {children}
      </DialogContent>
    </Dialog>
  )
}
