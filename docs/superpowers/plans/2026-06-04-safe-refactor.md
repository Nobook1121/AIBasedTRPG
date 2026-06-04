# Safe Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the current AI-based TRPG codebase safely while preserving current behavior and adding a maintainable logging, testing, and documentation foundation.

**Architecture:** Keep Flask, Flask-SocketIO, static HTML, vanilla JavaScript, Bootstrap, and current data files. Add tests and shared utilities first, then move route groups out of `server.py` into focused modules without changing URL paths, response shapes, DOM ids, or saved JSON formats.

**Tech Stack:** Python 3, Flask 2.0.1, Flask-Cors, Flask-SocketIO, bcrypt, pytest, Node `--check`, vanilla JavaScript, Bootstrap 5, CSS.

---

## File Structure

Create these backend files:

- `trpg_server/__init__.py`: package marker and public app imports.
- `trpg_server/app_factory.py`: Flask app and Socket.IO construction, blueprint registration, startup wiring.
- `trpg_server/settings.py`: path constants, default config, environment variables.
- `trpg_server/logging_config.py`: centralized logger setup, request logging, exception logging, secret redaction.
- `trpg_server/responses.py`: consistent JSON success and error helpers.
- `trpg_server/security.py`: permission decorator, safe path helpers, upload validation.
- `trpg_server/json_store.py`: UTF-8 JSON read/write with atomic writes.
- `trpg_server/network_discovery.py`: port checks, local IP lookup, UDP/TCP discovery helpers.
- `trpg_server/routes/scenarios.py`: scenario and scenario cover API routes.
- `trpg_server/routes/auth.py`: register, login, logout, auth status, profile update routes.
- `trpg_server/routes/assets.py`: static avatar, cover, AI platform icon, and config file serving.
- `trpg_server/routes/config.py`: general config, AI platform config, model JS config, API test routes.
- `trpg_server/routes/users.py`: admin user routes and IP config routes.
- `trpg_server/routes/chat.py`: chat and message routes.
- `trpg_server/routes/network.py`: network and penetration config/status/test routes.
- `trpg_server/routes/saves.py`: save, save node, autosave routes.
- `trpg_server/routes/pages.py`: index and static fallback routes.
- `trpg_server/socket_events.py`: Socket.IO connect, disconnect, send message, typing handlers.

Modify these existing backend files:

- `server.py`: turn into a small compatibility entry point that imports app/socketio and starts the server.
- `user_manager.py`: keep public `user_manager` behavior; migrate file I/O through `trpg_server.json_store` after tests exist.
- `requirements.txt`: add test dependency `pytest==8.4.0`.

Create these test and verification files:

- `tests/conftest.py`: temp app/data setup.
- `tests/test_json_store.py`: JSON atomic read/write behavior.
- `tests/test_security.py`: safe path and upload validation behavior.
- `tests/test_user_manager.py`: register/login/permission behavior.
- `tests/test_api_smoke.py`: key API route smoke tests.
- `scripts/verify.ps1`: repeatable local verification command.

Modify frontend files:

- `index.html`: remove duplicate script loading, preserve ids and layout.
- `js/main.js`: keep startup orchestration only.
- `js/dom-utils.js`: create safe DOM and event helpers.
- `js/api-client.js`: create shared `apiRequest`.
- `js/chat.js`, `js/auth.js`, `js/network.js`, `js/saves.js`, `js/platform-ui.js`, `js/scenario.js`, `js/tabs.js`: migrate duplicated fetch/error/event code gradually.
- `style.css`: introduce design tokens and stabilize controls/layouts.

Modify documentation:

- `README.md`: setup, startup, verification, configuration, troubleshooting.
- `docs/api.md`: API route overview.
- `docs/development.md`: module layout, logging, tests, data directories, safe file rules.

---

### Task 1: Verification Baseline

**Files:**
- Create: `scripts/verify.ps1`
- Create: `tests/conftest.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add pytest dependency**

Add this exact line to `requirements.txt` after the existing dependencies:

```text
pytest==8.4.0
```

- [ ] **Step 2: Create the verification script**

Create `scripts/verify.ps1`:

```powershell
$ErrorActionPreference = "Stop"

python -m py_compile server.py user_manager.py

$jsFiles = @(
  "tools\diceTool.js",
  "tools\toolManager.js",
  "config\TestRequestConfig.js",
  "config\ConfigManager.js",
  "config\AIPlatformManager.js",
  "js\models\ScenarioModel.js",
  "js\views\ScenarioView.js",
  "js\controllers\ScenarioController.js",
  "js\tabs.js",
  "js\platform-ui.js",
  "js\chat.js",
  "js\auth.js",
  "js\network.js",
  "js\saves.js",
  "js\scenario.js",
  "js\main.js"
)

foreach ($file in $jsFiles) {
  node --check $file
}

pytest -q
```

- [ ] **Step 3: Create test configuration fixture**

Create `tests/conftest.py`:

```python
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def temp_json_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run baseline checks**

Run:

```powershell
.\scripts\verify.ps1
```

Expected: Python and JavaScript syntax checks pass. At this point pytest may report `no tests ran` because only `tests/conftest.py` exists.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt scripts\verify.ps1 tests\conftest.py
git commit -m "test: add verification baseline"
```

---

### Task 2: Shared JSON Storage And Path Safety

**Files:**
- Create: `trpg_server/__init__.py`
- Create: `trpg_server/json_store.py`
- Create: `trpg_server/security.py`
- Create: `tests/test_json_store.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Write JSON store tests**

Create `tests/test_json_store.py`:

```python
from trpg_server.json_store import read_json, write_json_atomic


def test_read_json_returns_default_for_missing_file(tmp_path):
    path = tmp_path / "missing.json"

    result = read_json(path, default={"items": []})

    assert result == {"items": []}


def test_write_json_atomic_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "data.json"

    write_json_atomic(path, {"name": "scenario"})

    assert read_json(path) == {"name": "scenario"}
```

- [ ] **Step 2: Write path safety tests**

Create `tests/test_security.py`:

```python
import pytest

from trpg_server.security import is_allowed_upload, safe_join


def test_safe_join_allows_child_path(tmp_path):
    result = safe_join(tmp_path, "covers", "cover.png")

    assert result == tmp_path / "covers" / "cover.png"


def test_safe_join_rejects_parent_escape(tmp_path):
    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(tmp_path, "..", "users.json")


def test_is_allowed_upload_checks_extension_case_insensitively():
    assert is_allowed_upload("cover.PNG", {"png", "jpg"})
    assert not is_allowed_upload("cover.exe", {"png", "jpg"})
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```powershell
pytest tests\test_json_store.py tests\test_security.py -q
```

Expected: FAIL because `trpg_server.json_store` and `trpg_server.security` do not exist yet.

- [ ] **Step 4: Implement package marker**

Create `trpg_server/__init__.py`:

```python
"""Server package for the AI-based TRPG application."""
```

- [ ] **Step 5: Implement JSON storage**

Create `trpg_server/json_store.py`:

```python
import json
import os
from pathlib import Path
from typing import Any


def read_json(path: str | Path, default: Any = None) -> Any:
    json_path = Path(path)
    if not json_path.exists():
        return default

    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_atomic(path: str | Path, data: Any) -> None:
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = json_path.with_suffix(json_path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    os.replace(temp_path, json_path)
```

- [ ] **Step 6: Implement path safety helpers**

Create `trpg_server/security.py`:

```python
from pathlib import Path
from typing import Iterable


def safe_join(base_dir: str | Path, *parts: str) -> Path:
    base_path = Path(base_dir).resolve()
    candidate = base_path.joinpath(*parts).resolve()

    if candidate != base_path and base_path not in candidate.parents:
        raise ValueError(f"Unsafe path: {candidate}")

    return candidate


def is_allowed_upload(filename: str, allowed_extensions: Iterable[str]) -> bool:
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    allowed = {item.lower().lstrip(".") for item in allowed_extensions}
    return extension in allowed
```

- [ ] **Step 7: Run tests and verify pass**

Run:

```powershell
pytest tests\test_json_store.py tests\test_security.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add trpg_server tests\test_json_store.py tests\test_security.py
git commit -m "refactor: add storage and path safety helpers"
```

---

### Task 3: Central Logging System

**Files:**
- Create: `trpg_server/logging_config.py`
- Create: `tests/test_logging_config.py`
- Modify: `server.py`

- [ ] **Step 1: Write logging redaction test**

Create `tests/test_logging_config.py`:

```python
from trpg_server.logging_config import redact_sensitive


def test_redact_sensitive_masks_known_secret_keys():
    payload = {
        "api_key": "secret",
        "auth_token": "token",
        "password": "pass",
        "name": "public",
    }

    assert redact_sensitive(payload) == {
        "api_key": "***",
        "auth_token": "***",
        "password": "***",
        "name": "public",
    }
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
pytest tests\test_logging_config.py -q
```

Expected: FAIL because `trpg_server.logging_config` does not exist yet.

- [ ] **Step 3: Implement logging configuration**

Create `trpg_server/logging_config.py`:

```python
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"api_key", "auth_token", "token", "password", "secret", "secret_key"}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if key.lower() in SENSITIVE_KEYS else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def configure_logging(log_dir: str | Path = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / "ai_trpg.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def register_request_logging(app) -> None:
    logger = logging.getLogger("trpg_server.requests")

    @app.before_request
    def _start_request_timer():
        from flask import g

        g.request_started_at = time.perf_counter()

    @app.after_request
    def _log_response(response):
        from flask import g, request, session

        elapsed_ms = int((time.perf_counter() - g.get("request_started_at", time.perf_counter())) * 1000)
        logger.info(
            "%s %s status=%s elapsed_ms=%s user_id=%s client_ip=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
            session.get("user_id"),
            request.remote_addr,
        )
        return response
```

- [ ] **Step 4: Wire logging into current server entry**

At the top of `server.py`, after imports, add:

```python
from trpg_server.logging_config import configure_logging

configure_logging()
```

Do not remove existing `log_info`, `log_warning`, or `log_error` yet. They will be replaced after route extraction.

- [ ] **Step 5: Run verification**

Run:

```powershell
python -m py_compile server.py user_manager.py
pytest tests\test_logging_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add server.py trpg_server\logging_config.py tests\test_logging_config.py
git commit -m "refactor: add centralized logging setup"
```

---

### Task 4: Flask App Factory And Compatibility Entry

**Files:**
- Create: `trpg_server/settings.py`
- Create: `trpg_server/responses.py`
- Create: `trpg_server/app_factory.py`
- Modify: `server.py`
- Create: `tests/test_api_smoke.py`

- [ ] **Step 1: Add API smoke tests**

Create `tests/test_api_smoke.py`:

```python
from server import app


def test_index_serves_html():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_scenarios_endpoint_returns_json_shape():
    client = app.test_client()

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    data = response.get_json()
    assert "success" in data
    assert "data" in data
```

- [ ] **Step 2: Run smoke tests before extraction**

Run:

```powershell
pytest tests\test_api_smoke.py -q
```

Expected: PASS against current `server.py`.

- [ ] **Step 3: Create settings**

Create `trpg_server/settings.py`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

SCENARIOS_DIR = BASE_DIR / "scenarios"
SCENARIO_COVERS_DIR = BASE_DIR / "assets" / "scenario_covers"
AVATARS_DIR = BASE_DIR / "assets" / "avatars"
SAVES_DIR = BASE_DIR / "saves"
CONFIG_DIR = BASE_DIR / "config"
USERS_DIR = BASE_DIR / "users"
LOGS_DIR = BASE_DIR / "logs"

NETWORK_CONFIG_FILE = CONFIG_DIR / "network.json"
PENETRATION_CONFIG_FILE = CONFIG_DIR / "penetration.json"

DEFAULT_PORT = 8086
PORT_RETRY_COUNT = 5
PORT_RETRY_INTERVAL = 2
DISCOVERY_PORT = 50000
DISCOVERY_INTERVAL = 5

SECRET_KEY = os.environ.get("AI_TRPG_SECRET_KEY", "dev-only-change-me")
```

- [ ] **Step 4: Create response helpers**

Create `trpg_server/responses.py`:

```python
from flask import jsonify


def success_response(data=None, message="success", status=200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def error_response(message, status=400, error=None):
    payload = {"success": False, "message": message}
    if error:
        payload["error"] = error
    return jsonify(payload), status
```

- [ ] **Step 5: Create app factory shell**

Create `trpg_server/app_factory.py`:

```python
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from trpg_server.logging_config import configure_logging, register_request_logging
from trpg_server.settings import SECRET_KEY

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    configure_logging()
    app = Flask(__name__, static_folder="../assets", static_url_path="/assets")
    app.secret_key = SECRET_KEY
    CORS(app)
    socketio.init_app(app)
    register_request_logging(app)
    return app
```

- [ ] **Step 6: Keep server compatibility**

Modify `server.py` only in Task 5 after route groups have been extracted. For now, keep the existing `app` and `socketio` definitions to avoid breaking all decorators. This task establishes the factory without switching runtime behavior.

- [ ] **Step 7: Run verification**

Run:

```powershell
.\scripts\verify.ps1
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add trpg_server\settings.py trpg_server\responses.py trpg_server\app_factory.py tests\test_api_smoke.py
git commit -m "refactor: add app factory foundation"
```

---

### Task 5: Extract Backend Route Groups

**Files:**
- Create: route files under `trpg_server/routes/`
- Create: `trpg_server/socket_events.py`
- Modify: `trpg_server/app_factory.py`
- Modify: `server.py`

- [ ] **Step 1: Create route package**

Create `trpg_server/routes/__init__.py`:

```python
"""Route blueprints for the AI-based TRPG server."""
```

- [ ] **Step 2: Move route groups without changing logic**

Move these exact route ranges from `server.py` into blueprint modules. Keep function bodies as close as possible to the original for the first move:

```text
server.py:534-1047   -> trpg_server/routes/scenarios.py
server.py:1084-1285  -> trpg_server/routes/auth.py
server.py:1433-1483  -> trpg_server/routes/assets.py
server.py:1495-1736  -> trpg_server/routes/config.py
server.py:1759-1850  -> trpg_server/routes/users.py
server.py:1899-2287  -> trpg_server/routes/chat.py
server.py:2341-2773  -> trpg_server/routes/network.py
server.py:2796-3264  -> trpg_server/routes/saves.py
server.py:3318-3324  -> trpg_server/routes/pages.py
server.py:3330-3351  -> trpg_server/socket_events.py
```

Each route module must define `bp = Blueprint("<name>", __name__)` and replace `@app.route(...)` with `@bp.route(...)`.

- [ ] **Step 3: Register blueprints**

Update `trpg_server/app_factory.py`:

```python
def register_blueprints(app):
    from trpg_server.routes.assets import bp as assets_bp
    from trpg_server.routes.auth import bp as auth_bp
    from trpg_server.routes.chat import bp as chat_bp
    from trpg_server.routes.config import bp as config_bp
    from trpg_server.routes.network import bp as network_bp
    from trpg_server.routes.pages import bp as pages_bp
    from trpg_server.routes.saves import bp as saves_bp
    from trpg_server.routes.scenarios import bp as scenarios_bp
    from trpg_server.routes.users import bp as users_bp

    for blueprint in (
        scenarios_bp,
        auth_bp,
        assets_bp,
        config_bp,
        users_bp,
        chat_bp,
        network_bp,
        saves_bp,
        pages_bp,
    ):
        app.register_blueprint(blueprint)
```

Call `register_blueprints(app)` inside `create_app()` before returning the app.

- [ ] **Step 4: Switch server.py to compatibility entry**

After all blueprints compile, replace `server.py` with:

```python
from trpg_server.app_factory import create_app, socketio
from trpg_server.network_discovery import find_available_port, get_network_config
from trpg_server.settings import DEFAULT_PORT, PORT_RETRY_COUNT

app = create_app()


if __name__ == "__main__":
    network_config = get_network_config()
    preferred_port = int(network_config.get("port", DEFAULT_PORT))
    port = find_available_port(preferred_port, PORT_RETRY_COUNT)
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
```

If startup currently performs extra discovery-thread behavior, move that behavior into `trpg_server.network_discovery` before replacing `server.py`.

- [ ] **Step 5: Run verification after each route module**

After extracting each route module, run:

```powershell
python -m py_compile server.py user_manager.py
pytest tests\test_api_smoke.py -q
```

Expected: PASS after every module extraction.

- [ ] **Step 6: Run full verification**

Run:

```powershell
.\scripts\verify.ps1
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add server.py trpg_server tests
git commit -m "refactor: split flask routes into blueprints"
```

---

### Task 6: Migrate User And Config File I/O To Shared Storage

**Files:**
- Modify: `user_manager.py`
- Modify: `trpg_server/routes/config.py`
- Modify: `trpg_server/routes/network.py`
- Modify: `trpg_server/routes/saves.py`
- Modify: `trpg_server/routes/scenarios.py`
- Modify: `tests/test_user_manager.py`

- [ ] **Step 1: Add user manager tests**

Create `tests/test_user_manager.py`:

```python
from user_manager import UserManager


def test_check_permission_owner_has_admin_access():
    manager = UserManager()
    manager.users = [{"id": 1, "username": "owner", "role": "OWNER", "status": "active"}]

    assert manager.check_permission(1, "ADMIN")


def test_check_permission_user_lacks_admin_access():
    manager = UserManager()
    manager.users = [{"id": 1, "username": "user", "role": "USER", "status": "active"}]

    assert not manager.check_permission(1, "ADMIN")
```

- [ ] **Step 2: Run tests before I/O changes**

Run:

```powershell
pytest tests\test_user_manager.py -q
```

Expected: PASS.

- [ ] **Step 3: Replace direct JSON I/O**

In `user_manager.py`, import:

```python
from trpg_server.json_store import read_json, write_json_atomic
```

Change `_load_users` to:

```python
def _load_users(self):
    data = read_json(USERS_FILE, default={"users": []})
    return data.get("users", [])
```

Change `_save_users` to:

```python
def _save_users(self):
    try:
        write_json_atomic(USERS_FILE, {"users": self.users})
        return True
    except Exception as exc:
        print(f"Failed to save user data: {exc}")
        return False
```

Apply the same storage helper pattern to route modules that read/write JSON after extraction. Preserve existing data keys and indentation.

- [ ] **Step 4: Run verification**

Run:

```powershell
.\scripts\verify.ps1
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add user_manager.py trpg_server tests\test_user_manager.py
git commit -m "refactor: centralize json file storage"
```

---

### Task 7: Frontend Startup And Shared Helpers

**Files:**
- Create: `js/api-client.js`
- Create: `js/dom-utils.js`
- Modify: `index.html`
- Modify: `js/main.js`
- Modify: `js/chat.js`
- Modify: `js/auth.js`
- Modify: `js/network.js`
- Modify: `js/saves.js`
- Modify: `js/platform-ui.js`

- [ ] **Step 1: Create frontend API helper**

Create `js/api-client.js`:

```javascript
async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        },
        ...options
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok || data.success === false) {
        const message = data.message || data.error || `Request failed: ${response.status}`;
        throw new Error(message);
    }

    return data;
}
```

- [ ] **Step 2: Create DOM helper**

Create `js/dom-utils.js`:

```javascript
function getElement(id) {
    return document.getElementById(id);
}

function requireElement(id) {
    const element = getElement(id);
    if (!element) {
        throw new Error(`Missing required element: ${id}`);
    }
    return element;
}

function setText(id, value) {
    const element = getElement(id);
    if (element) {
        element.textContent = value ?? '';
    }
}

function on(parent, eventName, selector, handler) {
    parent.addEventListener(eventName, function(event) {
        const target = event.target.closest(selector);
        if (target && parent.contains(target)) {
            handler(event, target);
        }
    });
}
```

- [ ] **Step 3: Fix duplicate script loading**

In `index.html`, remove duplicate script tags from the `<head>` and keep scripts at the end of `<body>` in this order:

```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="tools/diceTool.js"></script>
<script src="tools/toolManager.js"></script>
<script src="config/TestRequestConfig.js"></script>
<script src="config/ConfigManager.js"></script>
<script src="config/AIPlatformManager.js"></script>
<script src="js/api-client.js"></script>
<script src="js/dom-utils.js"></script>
<script src="js/models/ScenarioModel.js"></script>
<script src="js/views/ScenarioView.js"></script>
<script src="js/controllers/ScenarioController.js"></script>
<script src="js/tabs.js"></script>
<script src="js/platform-ui.js"></script>
<script src="js/chat.js"></script>
<script src="js/auth.js"></script>
<script src="js/network.js"></script>
<script src="js/saves.js"></script>
<script src="js/scenario.js"></script>
<script src="js/main.js"></script>
```

- [ ] **Step 4: Keep main.js as startup coordinator**

Update `js/main.js` so `DOMContentLoaded` calls existing init functions in the current order. Preserve global names. Use guard checks only where DOM may be absent.

- [ ] **Step 5: Replace duplicated fetch paths gradually**

In one frontend module at a time, replace this pattern:

```javascript
const response = await fetch('/api/example');
const data = await response.json();
if (!response.ok || !data.success) {
    throw new Error(data.message || 'Request failed');
}
```

with:

```javascript
const data = await apiRequest('/api/example');
```

After each module, run `node --check` for that file.

- [ ] **Step 6: Run frontend verification**

Run:

```powershell
node --check js\api-client.js
node --check js\dom-utils.js
node --check js\main.js
node --check js\chat.js
node --check js\auth.js
node --check js\network.js
node --check js\saves.js
node --check js\platform-ui.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add index.html js
git commit -m "refactor: centralize frontend startup helpers"
```

---

### Task 8: CSS Tokens, Accessibility, And Layout Stability

**Files:**
- Modify: `style.css`
- Modify: `index.html`
- Modify: `js/main.js`
- Modify: `js/tabs.js`

- [ ] **Step 1: Add CSS tokens**

At the top of `style.css`, add:

```css
:root {
    --color-bg: #f6f7fb;
    --color-panel: #ffffff;
    --color-panel-muted: #f1f3f7;
    --color-text: #1f2933;
    --color-muted: #697386;
    --color-primary: #2f6fed;
    --color-primary-hover: #255fcf;
    --color-danger: #c83232;
    --color-success: #237a4b;
    --border-subtle: #d8dee9;
    --radius-sm: 4px;
    --radius-md: 8px;
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
}
```

Then replace repeated hard-coded values only where the replacement is obvious and behavior-neutral.

- [ ] **Step 2: Stabilize icon buttons**

Ensure sidebar and tool icon buttons have fixed dimensions:

```css
.sidebar-toggle,
.tool-tab-btn,
.btn-icon {
    width: 36px;
    min-width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
```

- [ ] **Step 3: Add missing accessibility attributes**

For interactive buttons that only show icons or symbols, add stable labels in `index.html`, for example:

```html
<button type="button" class="sidebar-toggle" id="sidebarToggle" title="Collapse sidebar" aria-label="Collapse sidebar" aria-expanded="true">
```

Do not change ids or visible text unless it fixes unreadable text caused by current encoding damage.

- [ ] **Step 4: Run verification**

Run:

```powershell
node --check js\main.js
node --check js\tabs.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add style.css index.html js\main.js js\tabs.js
git commit -m "style: improve ui tokens and accessibility states"
```

---

### Task 9: Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/api.md`
- Create: `docs/development.md`

- [ ] **Step 1: Update README**

Replace `README.md` with concise setup documentation:

````markdown
# AIBasedTRPG

AI-assisted TRPG host tool with a Flask backend and static HTML/CSS/JavaScript frontend.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python server.py
```

The server uses `config/network.json` for the preferred port and falls back to another available port if needed.

## Verify

```powershell
.\scripts\verify.ps1
```

## Data Directories

- `scenarios/`: scenario JSON files.
- `saves/`: save metadata, save nodes, and autosave data.
- `users/`: user JSON data and IP configs.
- `config/`: general, network, AI platform, and model configuration.
- `assets/`: avatars, scenario covers, and AI platform icons.

## Security Notes

Set `AI_TRPG_SECRET_KEY` in production-like environments. Logs are written to `logs/` and are ignored by git.
```
````

- [ ] **Step 2: Add API overview**

Create `docs/api.md` with route groups copied from `server.py`:

```markdown
# API Overview

## Scenarios

- `GET /api/scenarios`: list scenarios.
- `GET /api/scenarios/<scenario_id>`: read one scenario.
- `POST /api/scenarios`: create scenario.
- `PUT /api/scenarios/<scenario_id>`: update scenario.
- `DELETE /api/scenarios/<scenario_id>`: delete scenario.
- `POST /api/scenarios/cover`: upload scenario cover.
- `DELETE /api/scenarios/cover`: delete scenario cover.
- `POST /api/scenarios/cover/rename`: rename scenario cover.
- `GET /api/scenarios/list`: list scenario summaries.

## Auth And Users

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/status`
- `POST /api/auth/update`
- `GET /api/users`
- `PUT /api/users/<user_id>/role`
- `PUT /api/users/<user_id>/status`

## Config

- `POST /api/config/<config_name>`: save TOML-backed config.
- `POST /api/config/aiplatform/<platform>`: save AI platform config.
- `POST /api/config/aiplatform/<platform>/test`: test AI platform API connectivity.
- `POST /api/config/aimodel/save`: save model JS config.
- `POST /api/config/aimodel/delete`: delete model JS config.

## Chat

- `POST /api/chat`: send a chat request.
- `POST /api/messages`: send a home message.
- `POST /api/scenarios/<script_id>/messages`: send a scenario message.

## Network

- `GET /api/network/config`
- `POST /api/network/config`
- `GET /api/network/status`
- `POST /api/network/test`
- `GET /api/network/penetration/config`
- `POST /api/network/penetration/config`
- `GET /api/network/penetration/status`
- `GET /api/user/ip/config`
- `POST /api/user/ip/config`
- `GET /api/admin/ip/configs`

## Saves

- `GET /api/saves`
- `POST /api/saves`
- `DELETE /api/saves/<save_id>`
- `GET /api/saves/<save_id>/nodes`
- `POST /api/saves/<save_id>/nodes`
- `GET /api/saves/<save_id>/nodes/<node_filename>`
- `DELETE /api/saves/<save_id>/nodes/<node_filename>`
- `POST /api/saves/<save_id>/autosave`
- `GET /api/saves/<save_id>/autosave`

Existing response bodies keep the `success`, `message`, and `data` shape where currently used.
```

- [ ] **Step 3: Add development notes**

Create `docs/development.md`:

```markdown
# Development Notes

## Verification

Run `.\scripts\verify.ps1` before and after each refactor step.

## Logging

Use named Python loggers. Do not log passwords, API keys, auth tokens, uploaded file contents, or raw AI provider credentials.

## File Access

Use `trpg_server.security.safe_join` for request-controlled paths and `trpg_server.json_store.write_json_atomic` for JSON writes.

## Frontend

Keep global function names until all call sites are migrated. Prefer `apiRequest`, `setText`, `requireElement`, and delegated event handlers for new or refactored code.
```

- [ ] **Step 4: Run verification**

Run:

```powershell
.\scripts\verify.ps1
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add README.md docs\api.md docs\development.md
git commit -m "docs: document setup api and development workflow"
```

---

### Task 10: Final Smoke Test And Cleanup

**Files:**
- Modify only files needed to fix verification failures found in this task.

- [ ] **Step 1: Run full verification**

Run:

```powershell
.\scripts\verify.ps1
```

Expected: PASS.

- [ ] **Step 2: Start local server**

Run:

```powershell
python server.py
```

Expected: server starts on configured or fallback port and prints the selected URL/port.

- [ ] **Step 3: Manual smoke checklist**

In the browser, verify:

```text
Home tab loads.
Chat input accepts text.
Scenario list loads.
Scenario modal opens.
Settings tabs switch.
AI platform settings render.
Network status panel loads.
Save list loads.
Sidebar collapse/expand works.
No duplicate console initialization errors appear.
```

- [ ] **Step 4: Inspect logs**

Check `logs/ai_trpg.log`:

```text
Requests include method, path, status, elapsed time, user id when available, and client IP.
No password, API key, auth token, or provider secret appears in logs.
Log file size is bounded by rotation settings.
```

- [ ] **Step 5: Commit final fixes**

```powershell
git status --short
git add server.py user_manager.py trpg_server index.html style.css js README.md docs tests scripts requirements.txt
git commit -m "chore: finalize safe refactor verification"
```

Use the final commit only if verification fixes were needed. If no files changed, do not create an empty commit.
