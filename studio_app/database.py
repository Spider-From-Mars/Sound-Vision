"""Создание SQLite-базы приложения."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    salt BLOB NOT NULL,
    password_hash BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY, full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Звукорежиссёр', 'Администратор')),
    phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', specialization TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, purpose TEXT NOT NULL,
    hourly_rate INTEGER NOT NULL CHECK(hourly_rate >= 0)
);
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY, inventory_number TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Доступно',
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'Новый', created_at TEXT NOT NULL DEFAULT (date('now')),
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    engineer_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    starts_at TEXT NOT NULL, duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
    status TEXT NOT NULL DEFAULT 'Запланирован', cost INTEGER NOT NULL CHECK(cost >= 0),
    notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sessions_starts_at ON sessions(starts_at);
"""


class Database:
    def __init__(self, path: Path | None = None) -> None:
        seed = path is None
        if path is None:
            if os.name == "nt":
                root = Path(os.environ.get("APPDATA", Path.home()))
            elif os.uname().sysname == "Darwin":
                root = Path.home() / "Library" / "Application Support"
            else:
                root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
            path = root / "SoundVisionTkinter" / "studio.sqlite3"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        if seed:
            self._seed_demo_data()
        self.connection.commit()

    def _seed_demo_data(self) -> None:
        if self.connection.execute("SELECT COUNT(*) FROM clients").fetchone()[0]:
            return
        self.connection.executescript("""
            INSERT INTO clients(name, phone, email, notes)
                VALUES ('Группа «Север»', '+7 700 123-45-67', 'sever@example.kz', 'Демо-клиент');
            INSERT INTO employees(full_name, role, phone, email, specialization)
                VALUES ('Алексей Иванов', 'Звукорежиссёр', '+7 701 111-22-33', 'alex@example.kz', 'Запись и сведение');
            INSERT INTO employees(full_name, role, phone, email, specialization)
                VALUES ('Мария Соколова', 'Администратор', '+7 702 222-33-44', 'maria@example.kz', '');
            INSERT INTO rooms(name, purpose, hourly_rate) VALUES ('Зал A', 'Запись', 850000);
            INSERT INTO rooms(name, purpose, hourly_rate) VALUES ('Зал B', 'Сведение', 600000);
            INSERT INTO equipment(inventory_number, name, kind, room_id)
                VALUES ('MIC-001', 'Студийный микрофон', 'Микрофон', 1);
            INSERT INTO projects(title, client_id, status, notes)
                VALUES ('Демо-сингл', 1, 'В работе', 'Демонстрационный проект');
        """)
        start = (datetime.now() + timedelta(days=1)).replace(second=0, microsecond=0).isoformat()
        self.connection.execute(
            """INSERT INTO sessions(project_id, room_id, engineer_id, starts_at,
               duration_minutes, status, cost, notes)
               VALUES (1, 1, 1, ?, 120, 'Запланирован', 1700000, 'Демонстрационный сеанс')""",
            (start,),
        )

    def close(self) -> None:
        self.connection.close()
