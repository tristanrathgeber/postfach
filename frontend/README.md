# Postfach — Frontend

Local-first Mail-Client im Stil von Notion Mail. Vite + React 18 + TypeScript +
Tailwind CSS 3 + TanStack Query + cmdk. Schriften lokal gebündelt via
@fontsource (keine externen Requests).

## Entwicklung

```sh
npm install
npm run dev        # Vite auf :5173, Proxy /api → http://127.0.0.1:8722
```

Das Backend bedient den API-Vertrag aus `../docs/api-contract.md` unter `/api`.

## Build

```sh
npm run build      # tsc -b && vite build → dist/
```

## Tastatur

j/k wählen · Enter/o öffnen · e Archiv · # Papierkorb · u Ungelesen ·
r Antworten · c Verfassen · / Suche · g i Inbox · ⌘K Befehls-Palette
