import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// The theme file decides light or dark per the system setting; the shadcn pieces follow it through the dark class.
const root = document.documentElement
const scheme = window.matchMedia('(prefers-color-scheme: dark)')
const syncDark = () => root.classList.toggle('dark', getComputedStyle(root).colorScheme.includes('dark'))
syncDark()
scheme.addEventListener('change', syncDark)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
