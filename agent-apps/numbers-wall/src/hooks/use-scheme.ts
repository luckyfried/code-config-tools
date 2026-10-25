import { useEffect } from "react"

/** Mirrors the theme's color-scheme onto <html data-scheme>, which the components' dark variants read. */
export function useScheme() {
  useEffect(() => {
    const root = document.documentElement
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const apply = () => {
      const scheme = getComputedStyle(root).colorScheme
      root.dataset.scheme = scheme.includes("dark") ? "dark" : "light"
    }
    apply()
    media.addEventListener("change", apply)
    return () => media.removeEventListener("change", apply)
  }, [])
}
