"""Compatibility entry point for legacy imports.

The application now uses ``trpg_server.users.UserService``. This module keeps
old ``from user_manager import user_manager`` imports working without creating
or writing user files at import time.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from trpg_server.settings import USERS_DIR
from trpg_server.users.database import UserDatabase
from trpg_server.users.migrations import migrate_json_users
from trpg_server.users.service import UserService


class UserManager:
    def __init__(
        self,
        database_file: str | Path | None = None,
        users_file: str | Path | None = None,
        ip_config_dir: str | Path | None = None,
    ) -> None:
        self.database_file = Path(
            database_file
            or os.environ.get("AI_TRPG_USER_DATABASE_FILE")
            or USERS_DIR / "users.sqlite3"
        )
        self.users_file = Path(
            users_file
            or os.environ.get("AI_TRPG_USERS_FILE")
            or USERS_DIR / "users.json"
        )
        self.ip_config_dir = Path(
            ip_config_dir
            or os.environ.get("AI_TRPG_USER_IP_CONFIG_DIR")
            or USERS_DIR / "ip_configs"
        )
        self._service: UserService | None = None

    def _get_service(self) -> UserService:
        if self._service is None:
            db = UserDatabase(self.database_file)
            db.initialize()
            try:
                migrate_json_users(self.users_file, db)
            except (ValueError, sqlite3.Error):
                pass
            self._service = UserService(db, ip_config_dir=self.ip_config_dir)
        return self._service

    def __getattr__(self, name):
        return getattr(self._get_service(), name)


user_manager = UserManager()
