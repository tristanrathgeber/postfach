# Postfach

A local-first mail app in the spirit of Notion Mail — for any IMAP account
(self-hosted, GMX, web.de, Gmail, …). Everything runs on your own Mac
(`127.0.0.1:8722`). No account required to try it, **no telemetry**, and by
default **no cloud** — the AI runs entirely on your machine via Ollama.

**Emilia**, the built-in AI copilot, runs entirely locally through
[Ollama](https://ollama.com): answer questions about your mailbox (with source
chips), rewrite drafts in your own tone, search in plain German, summarize long
threads — all offline. Press ⌘J to open her.

## Privacy — verifiable, not just promised

Postfach makes **no network connection you didn't ask for.** There is no
analytics, no crash reporting, no phone-home. You can check this yourself:

| Where it connects | When | What for |
|---|---|---|
| Your mail provider (IMAP/SMTP) | while the app runs (IMAP IDLE push) + when you send | fetching and sending your mail |
| `localhost:11434` (Ollama) | Emilia, and local sort/draft (default) | the local AI model — never leaves your Mac |
| The unsubscribe host | only when you click "unsubscribe" (RFC-8058 one-click) | the sender's own unsubscribe endpoint |
| GitHub releases API | **only** when you click "Check for updates" | comparing your version to the latest |
| A cloud AI provider (Anthropic) | **only if** you turn off `sort_local`/`draft_local` | classifying/drafting — this sends mail content to the cloud |

The **About dialog** (⌘K → "Über Postfach") and `GET /api/network-info` list
exactly these targets at runtime — including the cloud AI host **if** you've
opted into it, so the panel can never quietly lie. `backend/tests/test_appreife.py`
asserts no telemetry/analytics package is imported anywhere. Out of the box, the
only outbound traffic is to your own mail server; everything else is a local call
(Ollama) or triggered by an explicit click.

**AI boundaries (test-enforced):** the AI classifies and drafts — it never sends,
moves, or deletes. Sending happens only when *you* click. Passwords live in the
macOS Keychain, never in a config file, log, or the search index. See
`backend/tests/test_safety.py`.

## Install as a Mac app (real binary — no uv/Node needed)

Download `Postfach.app.zip` from the
[latest release](https://github.com/tristanrathgeber/postfach/releases/latest),
unzip, and move `Postfach.app` to `/Applications`. It's a self-contained bundle
with an embedded Python — no toolchain required to run it. Unsigned, so on first
launch right-click → **Open**. Cold start ~0.5 s, ~145 MB idle.

A fresh install starts with no accounts — add yours in the window ("+ Konto
hinzufügen"): pick your provider, the server settings fill in, the password goes
straight to the Keychain. No YAML editing.

For Emilia, install [Ollama](https://ollama.com) and pull a model:
`ollama pull qwen3:8b` (chat) and `ollama pull all-minilm:l6-v2` (memory).

## Build from source

Requirements to *build*: macOS, [uv](https://docs.astral.sh/uv/), Node.js ≥ 20.

```bash
# Clone both repos SIDE BY SIDE (postfach uses email-agent as a path dependency):
git clone https://github.com/tristanrathgeber/email-agent
git clone https://github.com/tristanrathgeber/postfach
cd postfach

./scripts/build_app.sh          # → dist/Postfach.app (PyInstaller bundle)
cp -r dist/Postfach.app /Applications/
```

## Try it instantly (demo mode, no credentials)

```bash
cd backend && uv sync && cd ../frontend && npm install && npm run build && cd ..
POSTFACH_DEMO=1 uv run --project backend postfach   # → http://127.0.0.1:8722
```

## What's inside

- **Writing:** reply/compose with an "AI draft" in your style, forward with
  attachments, BCC, per-account signatures, local drafts (autosave), attachments
  (25 MB), contact autocomplete, snippets.
- **Receiving & triage:** bulk actions, spam handling, category correction, native
  macOS notifications, background auto-sorting (launchd).
- **Search:** local full-text (SQLite FTS5) with operators (`von:` `betreff:`
  `hat:anhang` …) plus natural-language search via Emilia (`?` prefix); 3–13 ms
  on thousands of mails.
- **Threads, snooze, send-later, follow-up** — a restart-safe local queue, no cloud.
- **Inbox hygiene:** subscription manager with one-click unsubscribe
  (RFC-8058 / List-Unsubscribe), first-contact screener (HEY-style).
- **Emilia II:** streaming answers, natural-language search, Sie/Du tone switch,
  on-demand thread summaries, a global AI off-switch.
- **Calendar & export:** answer ICS invitations inline (real RSVP), export any
  mail to Obsidian-ready Markdown, local entity chips (amounts, dates, tracking).
- **Onboarding:** account setup form, provider presets, folder-mapping assistant,
  gentle keyboard-shortcut teaching.

## Configuration (advanced / power users)

You can still hand-write `config/config.yaml` (accounts + taxonomy) and `.env`
(passwords) if you prefer — UI-added accounts live separately in
`data/accounts.json` and never touch your hand-written config. In the bundled
app, config and data live in `~/Library/Application Support/Postfach`.

```yaml
emilia:
  model: qwen3:8b       # local model for chat/rewrite (llama3.2 = smaller)
  sort_local: true      # default: classify locally. Set false to use Claude (sends mail to the cloud).
  draft_local: true     # default: draft locally. Set false to use Claude for higher-quality drafts.
```

Both default to `true` — a fresh install makes **no cloud calls**. Turning either
off is an explicit opt-in that sends mail content to Anthropic; the About dialog
then lists that host so it stays transparent.

## Development

- Backend tests: `cd backend && uv run pytest` (258 tests; IMAP/SMTP/LLM mocked)
- Frontend: `cd frontend && npm run dev` (Vite, proxy to 8722), `npm test`, `npm run lint`
- CI runs both on every push (`.github/workflows/ci.yml`); tagged pushes build and
  publish the `.app` (`release.yml`).
- Architecture & frozen API contract: `docs/superpowers/specs/…`, `docs/api-contract.md`

## License

MIT.
