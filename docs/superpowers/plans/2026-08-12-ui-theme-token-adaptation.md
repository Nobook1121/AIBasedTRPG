# UI Theme Token Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scattered UI style constants with named theme tokens, fix dark theme white remnants, and add a `pattern_cyber_2` theme.

**Architecture:** Add a dedicated theme token CSS file imported before existing styles, then migrate high-impact hard-coded styling to semantic CSS variables. Simplify `ConfigManager.applyTheme()` so body classes use canonical `theme-*` names while keeping legacy classes for selectors that remain during this pass.

**Tech Stack:** TypeScript, CSS custom properties, React/esbuild CSS import chain, static HTML fragments.

---

### Task 1: Add Theme Token Layer

**Files:**
- Create: `frontend/src/styles/00-theme-tokens.css`
- Modify: `frontend/src/react/app.css`

- [ ] **Step 1: Create `00-theme-tokens.css`**

Define light, dark, and cyber token sets, plus legacy variable aliases. Include Bootstrap-adjacent component overrides for cards, modals, forms, dropdowns, tables, and utility text.

- [ ] **Step 2: Import tokens first**

Update `frontend/src/react/app.css` so `@import "../styles/00-theme-tokens.css";` is the first import.

- [ ] **Step 3: Build smoke check**

Run: `npm run build:frontend`

Expected: build completes without CSS import errors.

### Task 2: Refactor Theme Selection Logic

**Files:**
- Modify: `frontend/src/app/config/ConfigManager.ts`
- Modify: `frontend/src/index/fragments/03-room-tools-auth-settings.html`

- [ ] **Step 1: Add theme option**

Add `<option value="pattern_cyber_2">赛博档案</option>` to `#themeSelect`.

- [ ] **Step 2: Simplify body class application**

Replace repeated dark/light class toggling with a canonical class map:

```ts
const themeClassNames = ["theme-light", "theme-dark", "theme-cyber-2", "light-theme", "dark-theme"];
```

Apply `theme-cyber-2` for `pattern_cyber_2`, `theme-dark dark-theme` for dark or system-dark, and `theme-light light-theme` otherwise.

- [ ] **Step 3: Typecheck**

Run: `npm run typecheck`

Expected: TypeScript completes without new errors.

### Task 3: Migrate High-Impact CSS To Tokens

**Files:**
- Modify: `frontend/src/styles/01-foundation-chat.css`
- Modify: `frontend/src/react/shell/sidebar.css`
- Modify: `frontend/src/styles/02-scenario-character.css`
- Modify: `frontend/src/styles/03-tools-settings-platform.css`
- Modify: `frontend/src/styles/04-auth-profile-overrides.css`

- [ ] **Step 1: Remove duplicate root ownership**

Move root token ownership out of `01-foundation-chat.css`; keep only component styles there.

- [ ] **Step 2: Replace hard-coded chat and Markdown styling**

Use chat, markdown, text, surface, border, shadow, radius, and font-size tokens for message bubbles, timestamps, Markdown borders, code blocks, table rows, and error blocks.

- [ ] **Step 3: Replace sidebar constants**

Use sidebar-specific tokens for navigation text, hover, active, and background.

- [ ] **Step 4: Replace common scenario/tools/auth constants**

Prioritize hard-coded white, gray, blue, black, and rgba surfaces that cause dark theme readability bugs. Leave truly layout-specific dimensions intact unless they are theme concerns.

- [ ] **Step 5: Build and typecheck**

Run: `npm run typecheck`

Expected: TypeScript passes.

Run: `npm run build:frontend`

Expected: frontend build passes.

### Task 4: Final Verification

**Files:**
- Inspect generated output under `dist/public`

- [ ] **Step 1: Search for remaining high-risk hard-coded surfaces**

Run: `rg -n "#fff|white|#ffffff|#f8f9fa|#2d2d2d|#1a1a1a|#007bff|rgba\\(255, 255, 255" frontend/src/styles frontend/src/react`

Expected: remaining matches are either token definitions, intentional transparent overlays, avatar radii, or low-risk legacy areas documented in final notes.

- [ ] **Step 2: Run final build**

Run: `npm run build:frontend`

Expected: build completes.
