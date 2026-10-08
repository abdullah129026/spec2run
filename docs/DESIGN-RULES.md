# Spec2Run Design Rules — Banned Tropes

> Every UI commit must be checked against this list.
> Source: `docs/DESIGN-BRIEF.md` (frontend research, 2026-10-07).

### What to AVOID — banned tropes
1. Purple/blue gradient backgrounds, buttons, or cards — anywhere, ever.
2. Glassmorphism (backdrop-blur cards over gradients) as a primary surface.
3. Emoji as UI icons. Use Lucide, 16px, `currentColor`, quiet.
4. "AI sparkle" (✨) iconography and "Powered by AI" badges. The AI is infrastructure; label features by what they *do* ("Spec", "Sandbox", "Diff"), not by the fact they're AI.
5. Marketing hero sections or landing-page copy inside the product. The studio IS the first viewport.
6. Gradient text headlines.
7. Stock unthemed Swagger UI. It must be reskinned dark (zinc + mono + indigo) or it ships looking grafted-on.
8. Raw log dumps. Logs are staged, timestamped, collapsible groups (Vercel-style) or they don't ship.
9. Blank panels. Every tab has an actionable empty state (clickable example prompt, import link).
10. Mic button with no live transcript feedback. Interim results stream into the prompt box or the button doesn't ship.
11. More than one accent color in the UI chrome. (Semantic red/amber/green are status, not accents.)
12. Hover-only controls. Everything must work on touch and on a projector.
13. Lorem ipsum / placeholder-looking sample content in the real UI.

## The short version

- Near-monochrome + ONE accent (`#5E6AD2` indigo). Color carries meaning, never decoration.
- Borders at ~7% white opacity. Elevation via background steps, not shadows.
- Inter for UI, JetBrains Mono for code/logs/URLs. 12–14px dense UI text.
- The studio is the product: split-screen Prompt Studio + Swagger/Code/Logs/Diff tabs, no marketing sections.
- Keyboard-first: logical tab order, Esc closes/stops, Enter submits. Shortcut chips where it matters.
- Motion: 150ms hover, 200–300ms transitions, ease-out cubic. Never linear.
- Dark is the native medium: `#09090b` canvas, `#101013`/`#18181b` surfaces.
