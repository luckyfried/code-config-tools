import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"
import { config } from "./lib/config"

// shadcn's dark variants follow the .dark class; studio is dark, ledger light, and auto follows the system.
const scheme = window.matchMedia("(prefers-color-scheme: dark)")
const applyScheme = () => {
  const dark = config.theme === "studio" || (config.theme === "auto" && scheme.matches)
  document.documentElement.classList.toggle("dark", dark)
}
applyScheme()
scheme.addEventListener("change", applyScheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
