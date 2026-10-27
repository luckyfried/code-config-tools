import { useEffect, useState } from "react"
import type { Article } from "@/types"

export type Size = { w: number; h: number }

const WAIT_MS = 1500

/**
 * Each story's picture size, read before the front page lays out, so a story's size on the page comes from its
 * picture's shape and nothing shifts once the pictures arrive. `ready` turns true when every picture has answered,
 * or after a short wait for the slow ones.
 */
export function useImageSizes(articles: Article[]) {
  const [sizes, setSizes] = useState<Map<string, Size | null>>(new Map())
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const wanted = articles.filter((a) => !sizes.has(a.image))
    if (!wanted.length) {
      if (articles.length) setReady(true)
      return
    }
    let stop = false
    const timer = window.setTimeout(() => !stop && setReady(true), WAIT_MS)
    Promise.all(
      wanted.map(
        (a) =>
          new Promise<[string, Size | null]>((done) => {
            const img = new Image()
            img.decoding = "async"
            img.onload = () => done([a.image, img.naturalWidth ? { w: img.naturalWidth, h: img.naturalHeight } : null])
            img.onerror = () => done([a.image, null])
            img.src = a.image
          }),
      ),
    ).then((found) => {
      if (stop) return
      setSizes((m) => new Map([...m, ...found]))
      setReady(true)
    })
    return () => {
      stop = true
      window.clearTimeout(timer)
    }
  }, [articles, sizes])

  return { sizes, ready }
}
