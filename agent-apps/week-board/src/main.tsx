import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "@fontsource-variable/inter/opsz.css"
import "./index.css"
import App from "./App.tsx"

// The theme file sets color-scheme; the shadcn parts read a .dark class, so it follows that value.
function followScheme() {
  const scheme = getComputedStyle(document.documentElement).colorScheme
  document.documentElement.classList.toggle("dark", scheme.trim() === "dark")
}
followScheme()
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", followScheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
