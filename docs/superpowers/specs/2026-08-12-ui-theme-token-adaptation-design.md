# UI Theme Token Adaptation Design

## Goal

Refactor frontend theme styling so colors, typography sizes, radii, shadows, overlays, and key component surfaces are referenced through named theme tokens instead of scattered hard-coded values. Fix dark theme white-surface remnants and add a `pattern_cyber_2` theme based on `docs/patterns/pattern_cyber_2.md`.

## Scope

This change covers the current web UI CSS and theme selection path:

- Global theme variables and compatibility aliases.
- `light`, `dark`, `system`, and `pattern_cyber_2` theme selection.
- Bootstrap-adjacent controls used by the existing templates.
- Chat bubbles, Markdown content, sidebar, settings/tools, auth/profile surfaces, and character-card UI areas.

It does not introduce a runtime theme editor, a remote theme registry, or large HTML layout rewrites.

## Architecture

Add a focused `frontend/src/styles/00-theme-tokens.css` file imported before existing CSS. This file owns all semantic theme keys and maps legacy variables such as `--color-bg` and `--color-primary` to the new keys so older CSS keeps working during migration.

Theme classes remain on `document.body`, but the implementation is simplified to use canonical class names:

- `theme-light`
- `theme-dark`
- `theme-cyber-2`

Compatibility classes `light-theme` and `dark-theme` may remain during this pass if existing selectors still depend on them, but new styling should target semantic tokens and the new `theme-*` names.

## Token Model

Tokens are grouped by responsibility:

- Base surfaces: `--theme-bg-page`, `--theme-bg-page-layer`, `--theme-bg-panel`, `--theme-bg-panel-muted`, `--theme-bg-elevated`.
- Text: `--theme-text-primary`, `--theme-text-secondary`, `--theme-text-muted`, `--theme-text-inverse`, `--theme-text-link`.
- Borders and focus: `--theme-border-subtle`, `--theme-border-strong`, `--theme-focus-ring`.
- Accent/status: `--theme-accent-primary`, `--theme-accent-primary-hover`, `--theme-accent-secondary`, `--theme-danger`, `--theme-success`, `--theme-warning`.
- Chat roles: `--theme-chat-other-bg`, `--theme-chat-player-bg`, `--theme-chat-kp-bg`, `--theme-chat-dice-bg`, and matching text/shadow tokens.
- Component shape and type: `--theme-radius-sm`, `--theme-radius-md`, `--theme-radius-pill`, `--theme-font-size-xs/sm/md/lg/xl`, `--theme-shadow-sm/md/lg`.

## Dark Theme Fix

The dark theme must set token values for forms, cards, modals, dropdowns, Markdown blocks, message bubbles, and utility text. Generic `.card`, `.modal-content`, `.form-control`, `.form-select`, `.text-muted`, `.list-group-item`, and `.table` selectors get token-based overrides so dark surfaces do not leave white blocks behind dark page backgrounds.

## Cyber Theme

`pattern_cyber_2` uses a deep blue-green black background, fluorescent green primary accent, cold blue secondary accent, translucent dark panels, and subtle grid texture. It should preserve tool readability and keep auth/profile forms usable by using tokenized form surfaces instead of forcing every input into a decorative terminal style.

## Testing

Run TypeScript checks and frontend build:

- `npm run typecheck`
- `npm run build:frontend`

Manual inspection should verify:

- Theme select includes the new cyber theme.
- Light theme still resembles the current UI.
- Dark theme uses dark panels and readable light text.
- Cyber theme applies the pattern colors and does not leave white text containers on dark backgrounds.
