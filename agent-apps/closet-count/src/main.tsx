import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App"
import { config } from "./lib/config"

/** theme.css says whether it is light or dark in --scheme; the dark class follows it so the components match. */
function syncScheme() {
  const scheme = getComputedStyle(document.documentElement).getPropertyValue("--scheme").trim()
  document.documentElement.classList.toggle("dark", scheme === "dark")
}
syncScheme()
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncScheme)
document.title = config.name

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
