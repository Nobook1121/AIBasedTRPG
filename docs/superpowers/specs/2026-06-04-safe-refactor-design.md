# Safe Refactor Design

## Goal

Refactor the current AI-based TRPG project while preserving existing behavior from the current working tree. The refactor must improve readability, maintainability, security, performance, testability, compatibility, reuse, frontend quality, and documentation without migrating the technology stack.

## Baseline

- Backend remains Flask and Flask-SocketIO.
- Frontend remains static HTML, CSS, and vanilla JavaScript with Bootstrap.
- Existing API paths, response shapes, DOM ids, saved data formats, and user-visible workflows remain compatible.
- Current uncommitted workspace behavior is treated as the functional baseline.

## Recommended Approach

Use a gradual safe refactor. Establish behavior checks first, then split modules and tighten risky implementation details step by step. Avoid a React, Next.js, or Vite migration in this phase because that would increase risk and make behavior preservation harder.

## Backend Architecture

`server.py` will be decomposed into focused modules while preserving all current routes:

- Application factory and startup configuration.
- Shared response helpers.
- Logging setup and request logging.
- Permission and session helpers.
- Scenario routes and services.
- Authentication and user routes.
- AI chat routes and Socket.IO handlers.
- Network and penetration configuration routes.
- Save and autosave routes.
- Static asset serving helpers.
- JSON file storage and path safety utilities.

Each extracted module should keep one clear responsibility. API routes should delegate file access and business rules to small service functions so they can be tested without running the full server.

## Security And Data Handling

File access must be restricted to explicit project directories:

- `scenarios/`
- `saves/`
- `assets/avatars/`
- `assets/scenario_covers/`
- `config/`
- `users/`

All request-controlled filenames and paths must be normalized and checked before use. Upload handling should validate allowed extensions, apply a file size limit, generate server-controlled file names, and avoid trusting user-provided paths.

JSON reads and writes should use a shared storage helper with:

- UTF-8 encoding.
- Directory creation.
- Clear error handling.
- Atomic writes through a temporary file and replace operation.
- Consistent indentation for human-readable data files.

Authentication remains session based with bcrypt password verification. The Flask secret key should come from an environment variable first, with a local development fallback that logs a warning. Permission checks keep the current role order: `OWNER > ADMIN > USER`.

## Logging Design

Replace scattered print-style logging with a centralized logging system:

- Use Python `logging` with named loggers per module.
- Keep console output for development and file output under `logs/`.
- Use one structured format for timestamp, level, module, request method, path, status code, elapsed time, user id when available, client IP, and message.
- Record exception stack traces for server errors.
- Add request lifecycle logging through Flask hooks.
- Avoid logging secrets, passwords, API keys, auth tokens, uploaded file contents, and raw AI provider credentials.
- Support log rotation by size or date to avoid unbounded log growth.
- Keep `*.log` ignored by git.

The goal is to make debugging API failures, startup issues, AI provider calls, network configuration changes, and save/scenario operations practical without exposing sensitive data.

## Frontend Architecture

The frontend will remain vanilla JavaScript. `index.html` should keep stable DOM ids and remove duplicate script loading. `js/main.js` should only coordinate startup. Business modules should manage their own initialization and state:

- Chat
- Auth
- Scenario management
- Save management
- Network configuration
- AI platform configuration
- Tabs and tools

Shared frontend helpers should cover:

- `apiRequest` with consistent error handling.
- Safe DOM text updates.
- Optional DOM lookup helpers.
- Event delegation helpers.
- Notification/toast rendering.
- Local storage schema and fallback handling.

Global mutable state should be reduced where practical, but public globals required by existing modules should be preserved until all call sites are migrated.

## Frontend Quality And Performance

Because this is not a React or Next.js app, Vercel React-specific rules do not apply directly. The refactor should still follow the same performance intent:

- Avoid unnecessary sequential requests when independent data can load in parallel.
- Avoid duplicate initialization.
- Use event delegation for repeated list items.
- Reduce repeated localStorage reads.
- Avoid full DOM replacement for large lists where targeted updates are enough.
- Lazy initialize heavy or rarely used panels when the related tab opens.
- Keep layout dimensions stable to reduce visual shifting.

UI changes should be restrained and behavior-preserving:

- Centralize CSS variables for colors, spacing, borders, and state colors.
- Improve button, form, modal, sidebar, chat, and settings states.
- Keep text inside containers at desktop and mobile sizes.
- Add missing `aria-label`, `aria-expanded`, and accessible status text where needed.
- Avoid nested card styling and decorative clutter.
- Preserve the TRPG workbench feel with clearer hierarchy and denser, usable controls.

## Testing Strategy

Testing starts with small behavior guards:

- Python syntax check for backend files.
- JavaScript syntax checks for all frontend scripts.
- Pytest coverage for config storage, path safety, user registration/login, scenario listing, save creation/loading, and permission failures.
- Flask test-client smoke tests for key API routes.
- Manual smoke test by starting the server and exercising the main tabs.

The first test additions should focus on behavior that may break during module extraction.

## Documentation

Documentation should describe real project behavior:

- `README.md`: setup, dependencies, startup, configuration, common troubleshooting.
- API route overview: method, path, purpose, auth requirement, request body, response shape.
- Development notes: module layout, logging, tests, data directories, safe file access rules.

No placeholder sections should be added.

## Implementation Order

1. Add verification commands and minimal tests for the current behavior.
2. Add shared backend utilities for responses, path safety, JSON storage, and logging.
3. Extract backend route groups from `server.py` while preserving all paths.
4. Add request lifecycle and exception logging.
5. Clean frontend script loading and startup orchestration.
6. Add shared frontend helpers and migrate high-risk `innerHTML` and duplicate event binding points.
7. Improve CSS variables, responsive layout, and accessibility states.
8. Update README and API documentation.
9. Run complete automated checks and a local server smoke test.

## Non-Goals

- No React, Next.js, Vite, TypeScript, database, or authentication-provider migration in this phase.
- No redesign that changes existing workflows.
- No API path or data format changes unless a compatibility wrapper keeps existing callers working.
- No unrelated feature development.

## Acceptance Criteria

- Existing workflows continue to work.
- Backend and frontend syntax checks pass.
- Added tests pass.
- Key API smoke tests pass.
- Server starts locally on an available port.
- Logs are useful, rotated or bounded, and do not include secrets.
- `server.py`, `index.html`, `style.css`, and large JS modules have clearer responsibilities.
- README and API documentation match implemented behavior.
