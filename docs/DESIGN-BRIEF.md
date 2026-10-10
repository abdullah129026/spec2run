# Spec2Run — Frontend Design Brief
**Project:** Spec2Run — Prompt to Microservice (split-screen API studio)
**Date:** 2026-10-07
**Constraint from user:** 10/10 UX/UI. Must NOT look like generic "AI slop." Must feel like a professional developer tool an examiner can drive live on a projector.

---

## 1. Developer-tool design languages worth emulating

Same discipline as PRISM's brief: near-monochrome + ONE accent, hairline borders, typography as the brand, density over decoration, keyboard-first, honest motion, dark as the native medium.

### Per-tool notes (Spec2Run edition)
| Tool | Steal this | Ignore this |
|---|---|---|
| **Vercel deploy logs** | The Logs tab bible: stage grouping, timestamped mono lines, collapsible sections, auto-scroll pinned to bottom, success panel with the URL + copy button | — |
| **Swagger UI** | The interaction model (expandable operations, "Try it out", auth dialog) | The stock green 2015 skin — reskin it dark or it will look grafted-on |
| **VS Code / Monaco** | File tree + editor tabs, command palette, minimap off by default, 13px mono | Settings-page complexity |
| **Linear** | Density, ⌘K palette, keyboard chips on actions | — |
| **GitHub PR "Files changed"** | The diff view reference: file list with +/- counts, unified diff, syntax colors | — |
| **Postman / Hoppscotch** | Auth helpers (paste token once, attached everywhere), environment switching = our sandbox switcher | UI clutter creep |
| **Warp** | Terminal-grade density for the Logs tab | — |

### Pro vs. AI slop, concretely (Spec2Run edition)
- Pro: the studio IS the landing page — first viewport is the tool, working. Slop: a hero section *describing* the tool above a "Launch app" button.
- Pro: Vercel-grade staged log streaming. Slop: a `<textarea>` dumping raw logs.
- Pro: Swagger UI themed to look native to the app. Slop: stock green Swagger iframed into a dark page (visual whiplash).
- Pro: one indigo accent on the Generate button. Slop: gradient "Generate ✨" button.
- Pro: empty tabs with clickable example prompts. Slop: blank panels saying "No data yet."
- Pro: mono timestamps, hashes, URLs. Slop: 18px marketing body copy inside the tool.

---

## 2. Prior art in API studios

### What works
- **Swagger Editor's live split** (spec left, preview right): editing one side updates the other instantly. Our Code/Swagger tabs should feel like that split, just tabbed.
- **Postman's auth model**: authenticate once, token attached to every request. Our "Try it out" must do this with the sandbox JWT — no pasting tokens per request.
- **Vercel's build logs**: stages as collapsible groups with per-line timestamps; the finale is a success panel, not just the last log line.

### What failed (and why)
- **Unthemed Swagger embeds**: every dark-mode tool that ships stock Swagger looks unfinished. *Lesson: budget the CSS override pass; it's not optional polish.*
- **Undifferentiated log walls**: without stage structure, users can't tell validating from deploying. *Lesson: the backend must emit staged events, not just lines.*

---

## 3. The studio layout, specified

Full-viewport app; the page never scrolls, panels scroll internally.

**Left — Prompt Studio (400–440px fixed):** product mark + sandbox status → prompt textarea → option chips (Auth / Database / Language) → Generate button → example prompts → "or import an OpenAPI file/URL" link.

**Right — generation workspace:** tab bar (Swagger | Code | Logs | Diff when a version exists). The tab bar's right side holds the session controls: sandbox status pill (building/live/expired), live URL chip + copy, Download ZIP, Push to GitHub.

A draggable divider between panels is a nice week-3 touch, not a requirement.

---

## 4. The tabs, specified

### Swagger tab
- `swagger-ui-react`, reskinned dark: zinc surfaces, mono paths, indigo "Try it out" and Authorize buttons. No green anywhere.
- **Auth flow**: an "Authorize" button opens a small dialog — either log in via the sandbox's own `/auth/login` to fetch a token, or paste one. "Try it out" then attaches `Authorization: Bearer …` automatically.
- The server URL chip shows the live sandbox URL; rebooting the sandbox updates it everywhere.

### Code tab
- Monaco with a custom `vs-dark`-derived theme on the zinc ramp, 13px JetBrains Mono, minimap off.
- File tree sidebar listing generated files; tabs for open files.
- Edits are local until you hit **"Apply edits & reboot"**, which re-boots the sandbox with your files. This is the "user can fix it" promise — it must work, not just exist.
- Download ZIP and Push to GitHub live in this tab's header.

### Logs tab
- Stages as collapsible groups: `Spec validated → Code rendered → Sandbox booting → Smoke tests`. Backend emits staged events; the UI never parses raw text to guess stages.
- 12px mono lines with timestamps; stage headers animate spinner → check on completion.
- Auto-scroll pinned to bottom; scrolling up unpins and shows a "jump to latest" pill.
- Finale: **success panel** — large live URL, copy button, "Open in Swagger" shortcut. **Failure panel** — which stage failed, the error in human words, retry button, "download full logs".

### Diff tab (appears when a versioned change exists)
- GitHub-PR style: file list with green/red +/- counts, unified diffs with syntax coloring; spec changes shown as a structured JSON diff, not raw text.

---

## 5. States for every async panel

- **Empty**: actionable — clickable example prompt, import link. Never blank, never "No data yet."
- **Loading**: skeleton blocks shaped like the eventual content, not a lone spinner.
- **Streaming** (logs): stage groups appear as work starts; lines fade in without layout shift.
- **Error**: names the failed stage, says what happened in plain words, offers retry + download logs.
- **Expired sandbox**: TTL notice with a one-click "reboot" button, not a dead URL.

---

## 6. Motion

150ms hover, 200–300ms tab/panel transitions, ease-out cubic — never linear, never default ease. Log lines fade+rise in 120ms with reserved space (no layout shift). Respect `prefers-reduced-motion`.

---

## 7. Type & color

- UI: Inter (system stack fallback acceptable). Code/logs/URLs/hashes: JetBrains Mono.
- Zinc ramp: canvas `#09090b`, surfaces `#101013` / `#18181b`, borders white at ~7%.
- Accent indigo `#5E6AD2`: primary actions, active tab underline, selection. Nothing else.
- Semantic colors are status only: emerald-500 success, red-500 error, amber-500 warning.

---

## 8. Responsive & projector

- Below ~1100px the split collapses into switchable views (Studio | Output toggle), not a squished split.
- Demo/projector: body text never below 13px. A week-3 "demo mode" toggle (larger base type, hides secondary chrome) is cheap and examiners notice.

---

## 9. Checklist for every UI commit

1. Does it look like Linear/Vercel shipped it? If it looks like a landing page, cut it.
2. Every async panel has empty, loading, error, and (where relevant) streaming states.
3. No gradients, no glassmorphism, no emoji icons, no ✨, no "Powered by AI" badges.
4. One accent color in the chrome. Semantic colors only for status.
5. Keyboard reachable: tab order sane, Esc closes, Enter submits.
6. Touch/projector usable: no hover-only controls.
