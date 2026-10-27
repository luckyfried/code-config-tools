import { useState } from "react"
import type { Article } from "@/types"
import { cn } from "@/lib/utils"

/**
 * A story's picture. On the front page it is drawn in its topic's duotone and pans slowly; a picture that cannot
 * load leaves its topic's color as a duotone field.
 */
export function Picture({
  article: a,
  size,
  duotone,
  className,
}: {
  article: Article
  size?: { w: number; h: number }
  duotone?: boolean
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  if (failed || !a.image) return <div className={cn("pic-field", className)} data-mark={a.headline.charAt(0)} aria-hidden="true" />
  const img = (
    <img
      className={duotone ? "pic-img" : cn("block size-full object-cover", className)}
      src={a.image}
      alt=""
      width={size?.w}
      height={size?.h}
      decoding="async"
      draggable={false}
      onError={() => setFailed(true)}
    />
  )
  return duotone ? <div className="pic-pan">{img}</div> : img
}
