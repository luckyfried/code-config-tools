import { ArrowUpRight } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog"
import type { Item } from "@/lib/config"

/** The full-size picture, opened from a card. */
export function PictureDialog({
  item,
  thumb,
  priceText,
  onClose,
}: {
  item: Item | null
  thumb: string | null
  priceText: string
  onClose: () => void
}) {
  return (
    <Dialog open={item !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="gap-0 overflow-hidden rounded-2xl p-0 sm:max-w-2xl">
        {item && (
          <>
            <div className="stage !aspect-square !rounded-none sm:!aspect-[4/3]">
              <span className="plinth" />
              {item.image && (
                <img
                  className="picture"
                  src={item.image}
                  alt={item.name}
                  style={thumb ? { backgroundImage: `url(${thumb})`, backgroundSize: "contain", backgroundRepeat: "no-repeat", backgroundPosition: "50% 100%" } : undefined}
                />
              )}
            </div>
            <div className="flex items-start justify-between gap-4 p-5">
              <div className="min-w-0">
                <DialogTitle className="display text-[1.35rem] leading-tight font-semibold">{item.name}</DialogTitle>
                <DialogDescription className="mt-1 text-[0.92rem]">{item.note}</DialogDescription>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <span className="display text-[1.35rem] font-semibold text-primary tabular-nums">{priceText}</span>
                {item.url && (
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[0.85rem] text-muted-foreground hover:text-foreground hover:underline">
                    {new URL(item.url).hostname.replace(/^www\./, "")}
                    <ArrowUpRight className="size-3.5" />
                  </a>
                )}
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
