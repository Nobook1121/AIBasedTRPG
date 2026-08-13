# TypeScript And File Safety Migration

## Goal

Keep the current Flask-based self-hosted platform working while adding a TypeScript frontend build path and a stricter file-write security model. The application must remain easy to run locally with `python server.py`, and it must also work when exposed through LAN, user-managed tunneling, user-managed virtual networking, or a cloud reverse proxy.

## Non-Goals

- Do not implement tunneling or virtual networking inside this application.
- Do not replace Flask with a TypeScript backend.
- Do not require Docker, Node process managers, or external services for basic local use.
- Do not allow guests to write arbitrary files on the host.

## Architecture Direction

The backend remains Flask. It owns authentication, authorization, file validation, path safety, JSON persistence, and static asset serving. The frontend is migrated incrementally from global JavaScript modules to TypeScript modules compiled into browser-ready JavaScript.

During migration, legacy JavaScript and compiled TypeScript can coexist. `index.html` should continue loading stable browser assets from `js/` or a generated static output folder. The server start command remains `python server.py`; frontend build commands are only needed when developing or changing frontend source.

## File-Write Security Model

Every endpoint that changes host files must pass through one backend policy:

- The target directory must be an explicit application data directory.
- The final path must be produced with `safe_join`.
- User-controlled filenames must be normalized to a safe basename.
- Uploads must be checked by extension, size, and detected content type where practical.
- JSON writes must use `write_json_atomic`.
- Write operations must require an active session.
- Role checks must be explicit:
  - `OWNER` and `ADMIN` can manage platform-level files and users.
  - Authenticated users can update their own avatar.
  - Authenticated users can create/import scenarios.
  - Scenario update/delete requires ownership or elevated role once scenario ownership is recorded.
- Static reads may remain public for avatars, scenario covers, and scenario data intended for players.

## Scenario Repair Scope

Scenario create, edit, delete, import, and cover upload must write through backend APIs. The frontend must not treat `localStorage` as the source of truth for host files. `localStorage` may only be a temporary cache for display recovery.

Scenario cover URLs must use one canonical public prefix:

```text
/assets/scenario_covers/<filename>
```

Backend file paths must never use this URL prefix directly as a filesystem path. They must extract a basename and resolve it against `SCENARIO_COVERS_DIR`.

## TypeScript Migration Scope

Migrate frontend modules in this order:

1. API client and shared browser utilities.
2. Scenario model, view, controller, and cover upload flow.
3. Auth state and session handling.
4. Saves and chat.
5. Network and AI platform configuration UI.
6. Remaining legacy entrypoints.

Each step must keep the generated browser asset compatible with the existing page. Once a TypeScript module fully replaces an old JavaScript file, delete the old file and remove it from `scripts/verify.ps1` and `index.html`.

## Testing Strategy

- Backend file-write policy uses pytest unit tests and route tests.
- Scenario repair uses route tests plus static frontend regression tests until a browser test runner exists.
- TypeScript build adds `npm run typecheck` and `npm run build` to verification.
- Existing `.\scripts\verify.ps1` remains the single full verification command.
- Runtime smoke still checks `/`, `/api/scenarios`, and `/api/network/config`.

## Implementation Order

1. Add a backend file-write policy module and tests.
2. Require login and safe ownership metadata for scenario writes.
3. Fix scenario edit/import/cover URL flow to use backend APIs and canonical URLs.
4. Add a minimal TypeScript toolchain.
5. Migrate scenario-related frontend code first.
6. Expand migration across the remaining frontend modules.
7. Delete replaced legacy files and update docs.
