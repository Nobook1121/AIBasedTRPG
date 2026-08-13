from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_backend_package_lives_under_backend_directory():
    assert (ROOT / "backend/trpg_server/app_factory.py").is_file()
    assert (ROOT / "backend/trpg_server/routes/pages.py").is_file()
    assert not (ROOT / "trpg_server").exists()


def test_root_server_py_remains_compatibility_entrypoint():
    source = (ROOT / "server.py").read_text(encoding="utf-8")

    assert "backend" in source
    assert "from trpg_server.app_factory import create_app, socketio" in source


def test_backend_package_imports_from_repo_root_python_process():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    result = subprocess.run(
        [sys.executable, "-c", "import trpg_server; print(trpg_server.__file__)"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "backend" in result.stdout
