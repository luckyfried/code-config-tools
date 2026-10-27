import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "@/App"
import { config } from "@/config"
import "@/index.css"

// theme.css says whether it is dark; the shadcn components read that from a class on the page.
const root = document.documentElement
const syncScheme = () => root.classList.toggle("dark", getComputedStyle(root).getPropertyValue("--scheme").trim() === "dark")
syncScheme()
document.title = config.name
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncScheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
