import { useLayoutEffect } from "react"

/**
 * theme.css says whether the editor's chrome is light or dark through `color-scheme`; the components' dark styles
 * follow it through the `dark` class, kept in step when the device switches.
 */
export function useChromeScheme() {
  useLayoutEffect(() => {
    const root = document.documentElement
    const sync = () => root.classList.toggle("dark", getComputedStyle(root).colorScheme.trim() === "dark")
    sync()
    const list = window.matchMedia("(prefers-color-scheme: dark)")
    list.addEventListener("change", sync)
    return () => list.removeEventListener("change", sync)
  }, [])
}
