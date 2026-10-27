import { useEffect, useState } from "react"

const WIDTH = 720
const made = new Map<string, Promise<string>>()

/** A picture wider than the card needs is drawn once at load into a 720 px copy; the card shows the copy. */
function thumbnail(src: string): Promise<string> {
  let job = made.get(src)
  if (!job) {
    job = (async () => {
      if (typeof OffscreenCanvas === "undefined" || typeof createImageBitmap === "undefined") return src
      const blob = await (await fetch(src)).blob()
      const probe = await createImageBitmap(blob)
      if (probe.width <= WIDTH * 1.25) {
        probe.close()
        return src
      }
      const height = Math.round((probe.height / probe.width) * WIDTH)
      probe.close()
      const bitmap = await createImageBitmap(blob, { resizeWidth: WIDTH, resizeHeight: height, resizeQuality: "high" })
      const canvas = new OffscreenCanvas(WIDTH, height)
      canvas.getContext("2d")?.drawImage(bitmap, 0, 0)
      bitmap.close()
      const small = await canvas.convertToBlob({ type: "image/webp", quality: 0.9 })
      return URL.createObjectURL(small)
    })().catch(() => src)
    made.set(src, job)
  }
  return job
}

export function useThumb(src: string | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!src) return
    let live = true
    thumbnail(src).then((u) => live && setUrl(u))
    return () => {
      live = false
    }
  }, [src])
  return src ? url : null
}
