import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "@fontsource-variable/inter/opsz.css"
import "@fontsource-variable/literata/opsz.css"
import "./index.css"
import App from "./App"

// theme.css names its own scheme; the dark class follows it, and follows the device when the theme is auto.
const scheme = () => {
  const s = getComputedStyle(document.documentElement).getPropertyValue("--scheme").trim()
  document.documentElement.classList.toggle("dark", s === "dark")
}
scheme()
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", scheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
