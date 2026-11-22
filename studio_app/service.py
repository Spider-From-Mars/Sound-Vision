"""Сервисные сценарии и преобразование записей БД в объекты предметной области."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .models import (
    Client,
    Employee,
    Equipment,
    EquipmentStatus,
    Project,
    ProjectStatus,
    RecordingSession,
    Room,
    RoomPurpose,
    SessionStatus,
    SoundEngineer,
    Studio,
    StudioAdministrator,
)

TABLES = {"clients", "employees", "rooms", "equipment", "projects", "sessions"}


class StudioService:
    """CRUD, расписание и загрузка доменной модели из SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    def rows(self, table: str) -> list[sqlite3.Row]:
        if table not in TABLES:
            raise ValueError("Неизвестный раздел.")
        queries = {
            "clients": "SELECT * FROM clients ORDER BY id DESC",
            "employees": "SELECT * FROM employees ORDER BY id DESC",
            "rooms": "SELECT * FROM rooms ORDER BY id DESC",
            "equipment": "SELECT e.*, r.name AS room FROM equipment e LEFT JOIN rooms r ON r.id=e.room_id ORDER BY e.id DESC",
            "projects": "SELECT p.*, c.name AS client FROM projects p JOIN clients c ON c.id=p.client_id ORDER BY p.id DESC",
            "sessions": """SELECT s.*, p.title AS project, c.name AS client, r.name AS room,
                e.full_name AS engineer FROM sessions s JOIN projects p ON p.id=s.project_id
                JOIN clients c ON c.id=p.client_id JOIN rooms r ON r.id=s.room_id
                JOIN employees e ON e.id=s.engineer_id ORDER BY s.starts_at""",
        }
        return list(self.db.execute(queries[table]))

    def choices(
        self, table: str, where: str = "", params: tuple[Any, ...] = ()
    ) -> list[sqlite3.Row]:
        if table not in {"clients", "employees", "rooms", "projects", "equipment"}:
            raise ValueError("Неизвестный раздел для выбора.")
        return list(self.db.execute(f"SELECT * FROM {table} {where} ORDER BY id", params))

    def get(self, table: str, object_id: int) -> sqlite3.Row | None:
        if table not in TABLES:
            raise ValueError("Неизвестный раздел.")
        return self.db.execute(f"SELECT * FROM {table} WHERE id=?", (object_id,)).fetchone()

    def save(self, table: str, values: dict[str, Any], object_id: int | None = None) -> int:
        if table not in TABLES or not values:
            raise ValueError("Некорректные данные для сохранения.")
        fields = ", ".join(values)
        args = tuple(values.values())
        try:
            if object_id is None:
                cursor = self.db.execute(
                    f"INSERT INTO {table} ({fields}) VALUES ({', '.join('?' for _ in values)})",
                    args,
                )
                result = int(cursor.lastrowid)
            else:
                updates = ", ".join(f"{field}=?" for field in values)
                self.db.execute(f"UPDATE {table} SET {updates} WHERE id=?", (*args, object_id))
                result = object_id
            self.db.commit()
            return result
        except sqlite3.Error:
            self.db.rollback()
            raise

    def delete(self, table: str, object_id: int) -> None:
        if table not in TABLES:
            raise ValueError("Неизвестный раздел.")
        self.db.execute(f"DELETE FROM {table} WHERE id=?", (object_id,))
        self.db.commit()

    def schedule(self, values: dict[str, Any], session_id: int | None = None) -> int:
        start = datetime.fromisoformat(values["starts_at"])
        duration = int(values["duration_minutes"])
        if duration <= 0:
            raise ValueError("Длительность должна быть больше нуля.")
        old = self.get("sessions", session_id) if session_id else None
        if start < datetime.now().replace(second=0, microsecond=0) and (
            not old or old["starts_at"] != values["starts_at"]
        ):
            raise ValueError("Нельзя запланировать сеанс в прошлом.")
        end = start + timedelta(minutes=duration)
        for field, error in (
            ("room_id", "Помещение уже занято в это время."),
            ("engineer_id", "Звукорежиссёр уже занят в это время."),
        ):
            conflicts = self.db.execute(
                f"SELECT starts_at, duration_minutes FROM sessions WHERE {field}=? AND status NOT IN ('Отменён','Завершён') AND id != ?",
                (values[field], session_id or -1),
            )
            for row in conflicts:
                other_start = datetime.fromisoformat(row["starts_at"])
                if (
                    start < other_start + timedelta(minutes=row["duration_minutes"])
                    and other_start < end
                ):
                    raise ValueError(error)
        rate = self.db.execute(
            "SELECT hourly_rate FROM rooms WHERE id=?", (values["room_id"],)
        ).fetchone()
        if rate is None:
            raise ValueError("Выберите существующее помещение.")
        values["cost"] = int(
            (Decimal(rate[0]) * duration / 60).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )
        return self.save("sessions", values, session_id)

    def change_session_status(self, session_id: int, status: str) -> None:
        row = self.get("sessions", session_id)
        transitions = {
            "Запланирован": {"Подтверждён", "Отменён"},
            "Подтверждён": {"Завершён", "Отменён"},
            "Завершён": set(),
            "Отменён": set(),
        }
        if row is None or status not in transitions[row["status"]]:
            raise ValueError("Такой переход статуса сеанса невозможен.")
        self.db.execute("UPDATE sessions SET status=? WHERE id=?", (status, session_id))
        self.db.commit()

    def load_studio(self) -> Studio:
        """Загружает связанные SQLite-записи в реальные экземпляры доменных классов."""
        studio = Studio("Sound & Vision")
        clients = {
            r["id"]: Client(r["id"], r["name"], r["phone"], r["email"])
            for r in self.choices("clients")
        }
        rooms = {
            r["id"]: Room(
                r["id"], r["name"], RoomPurpose(r["purpose"]), Decimal(r["hourly_rate"]) / 100
            )
            for r in self.choices("rooms")
        }
        employees: dict[int, Employee] = {}
        for row in self.choices("employees"):
            cls = SoundEngineer if row["role"] == "Звукорежиссёр" else StudioAdministrator
            employees[row["id"]] = (
                cls(row["id"], row["full_name"], row["phone"], row["email"], row["specialization"])
                if cls is SoundEngineer
                else cls(row["id"], row["full_name"], row["phone"], row["email"])
            )
        projects = {
            r["id"]: Project(
                r["id"],
                r["title"],
                clients[r["client_id"]],
                ProjectStatus(r["status"]),
                created_at=date.fromisoformat(r["created_at"]),
                notes=r["notes"],
            )
            for r in self.choices("projects")
        }
        for row in self.choices("equipment"):
            item = Equipment(
                row["id"],
                row["inventory_number"],
                row["name"],
                row["kind"],
                EquipmentStatus(row["status"]),
            )
            if row["room_id"] in rooms:
                item.assign_to(rooms[row["room_id"]])
        for row in self.db.execute("SELECT * FROM sessions ORDER BY starts_at"):
            engineer = employees.get(row["engineer_id"])
            if not isinstance(engineer, SoundEngineer):
                continue
            session = RecordingSession(
                row["id"],
                datetime.fromisoformat(row["starts_at"]),
                row["duration_minutes"],
                projects[row["project_id"]],
                rooms[row["room_id"]],
                engineer,
                SessionStatus(row["status"]),
            )
            session.project.add_session(session)
            session.room.sessions.append(session)
            engineer.accept_session(session)
        studio.clients.extend(clients.values())
        studio.rooms.extend(rooms.values())
        studio.employees.extend(employees.values())
        studio.projects.extend(projects.values())
        return studio
