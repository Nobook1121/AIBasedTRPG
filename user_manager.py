#!/usr/bin/env python3
"""User management for registration, login, permissions, and IP preferences."""

import logging
import time
from pathlib import Path

import bcrypt

from trpg_server.json_store import read_json, write_json_atomic

USERS_FILE = "users/users.json"
USER_IP_CONFIG_DIR = "users/ip_configs"
logger = logging.getLogger(__name__)

Path("users").mkdir(parents=True, exist_ok=True)
Path(USER_IP_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
if not Path(USERS_FILE).exists():
    write_json_atomic(USERS_FILE, {"users": []})


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"


def _ip_config_path(ip_address):
    return Path(USER_IP_CONFIG_DIR) / f'{ip_address.replace(".", "_")}.json'


class UserManager:
    """Manage local users and per-IP configuration files."""

    def __init__(self):
        self.users = self._load_users()

    def _load_users(self):
        try:
            data = read_json(USERS_FILE, default={"users": []})
            return data.get("users", [])
        except Exception:
            logger.exception("Failed to load user data")
            return []

    def _save_users(self):
        try:
            write_json_atomic(USERS_FILE, {"users": self.users})
            return True
        except Exception:
            logger.exception("Failed to save user data")
            return False

    def _hash_password(self, password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def _verify_password(self, password, hashed_password):
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    def register(self, username, password, email, ip_address=None):
        for user in self.users:
            if user["username"] == username:
                return False, "Username already exists"

        user_id = max([user["id"] for user in self.users], default=0) + 1
        new_user = {
            "id": user_id,
            "username": username,
            "password": self._hash_password(password),
            "email": email,
            "role": "USER",
            "created_at": _now_iso(),
            "last_login": _now_iso(),
            "character_cards": [],
            "status": "active",
            "avatar": "https://via.placeholder.com/40",
        }
        self.users.append(new_user)

        if self._save_users():
            return True, "Registration successful"
        return False, "Registration failed"

    def login(self, username, password, ip_address=None):
        for user in self.users:
            if user["username"] == username and user["status"] == "active":
                if self._verify_password(password, user["password"]):
                    user["last_login"] = _now_iso()
                    self._save_users()
                    return True, "Login successful", user
                return False, "Incorrect password", None

        return False, "User does not exist", None

    def get_user_by_id(self, user_id):
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None

    def get_user_by_username(self, username):
        for user in self.users:
            if user["username"] == username:
                return user
        return None

    def update_user_role(self, user_id, role):
        for user in self.users:
            if user["id"] == user_id:
                user["role"] = role
                self._save_users()
                return True, "Role updated successfully"
        return False, "User does not exist"

    def update_user_status(self, user_id, status):
        for user in self.users:
            if user["id"] == user_id:
                user["status"] = status
                self._save_users()
                return True, "Status updated successfully"
        return False, "User does not exist"

    def get_all_users(self):
        return self.users

    def check_permission(self, user_id, required_role):
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        role_levels = {
            "OWNER": 3,
            "ADMIN": 2,
            "USER": 1,
        }
        user_level = role_levels.get(user["role"], 0)
        required_level = role_levels.get(required_role, 0)
        return user_level >= required_level

    def create_ip_config(self, ip_address):
        config = {
            "ip_address": ip_address,
            "created_at": _now_iso(),
            "last_accessed": _now_iso(),
            "settings": {},
            "preferences": {},
        }
        try:
            write_json_atomic(_ip_config_path(ip_address), config)
            return True
        except Exception:
            logger.exception("Failed to create IP config")
            return False

    def get_ip_config(self, ip_address):
        config_file = _ip_config_path(ip_address)
        try:
            if not config_file.exists():
                return None

            config = read_json(config_file, default={})
            config["last_accessed"] = _now_iso()
            write_json_atomic(config_file, config)
            return config
        except Exception:
            logger.exception("Failed to get IP config")
            return None

    def update_ip_config(self, ip_address, config_data):
        config_file = _ip_config_path(ip_address)
        try:
            if not config_file.exists():
                return False

            config = read_json(config_file, default={})
            config.update(config_data)
            config["last_accessed"] = _now_iso()
            write_json_atomic(config_file, config)
            return True
        except Exception:
            logger.exception("Failed to update IP config")
            return False

    def delete_ip_config(self, ip_address):
        config_file = _ip_config_path(ip_address)
        try:
            if config_file.exists():
                config_file.unlink()
                return True
            return False
        except Exception:
            logger.exception("Failed to delete IP config")
            return False

    def get_all_ip_configs(self):
        configs = []
        try:
            for config_file in Path(USER_IP_CONFIG_DIR).glob("*.json"):
                if config_file.is_file():
                    configs.append(read_json(config_file, default={}))
            return configs
        except Exception:
            logger.exception("Failed to list IP configs")
            return []


user_manager = UserManager()
