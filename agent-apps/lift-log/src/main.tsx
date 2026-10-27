import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"

/* theme.css sets color-scheme; the dark variant of the components follows it. */
const root = document.documentElement
const syncScheme = () => root.classList.toggle("dark", getComputedStyle(root).colorScheme.trim() === "dark")
syncScheme()
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncScheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
