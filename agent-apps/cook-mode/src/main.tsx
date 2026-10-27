import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"

// shadcn's dark variants follow the theme: midnight always, auto when the device is dark.
const root = document.documentElement
const theme = window.__APP_CONFIG__?.theme ?? "auto"
const dark = window.matchMedia("(prefers-color-scheme: dark)")
const applyScheme = () => root.classList.toggle("dark", theme === "midnight" || (theme === "auto" && dark.matches))
applyScheme()
dark.addEventListener("change", applyScheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
