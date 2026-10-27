import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"
import { setCopy } from "@/lib/copy"

const config = window.__APP_CONFIG__
setCopy(config?.copy)
const root = createRoot(document.getElementById("root")!)
root.render(
  <StrictMode>
    {config ? (
      <App config={config} />
    ) : (
      <p style={{ padding: "2rem", fontFamily: "system-ui" }}>
        Your recipe box is not set up yet. Ask your agent to set it up.
      </p>
    )}
  </StrictMode>,
)
