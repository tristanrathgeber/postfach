import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Schriften lokal gebündelt (@fontsource) — keine externen Font-/CDN-Requests.
import '@fontsource-variable/instrument-sans'
import '@fontsource/newsreader/400.css'
import '@fontsource/newsreader/400-italic.css'
import '@fontsource/newsreader/500-italic.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
