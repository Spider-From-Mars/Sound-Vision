"""Объектная модель студии звукозаписи для учебного проекта."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class RoomPurpose(StrEnum):
    RECORDING = "Запись"
    MIXING = "Сведение"
    REHEARSAL = "Репетиционная"
    UNIVERSAL = "Универсальная"


class EquipmentStatus(StrEnum):
    AVAILABLE = "Доступно"
    MAINTENANCE = "На обслуживании"


class ProjectStatus(StrEnum):
    NEW = "Новый"
    IN_PROGRESS = "В работе"
    PAUSED = "На паузе"
    COMPLETED = "Завершён"


class SessionStatus(StrEnum):
    PLANNED = "Запланирован"
    CONFIRMED = "Подтверждён"
    FINISHED = "Завершён"
    CANCELLED = "Отменён"


@dataclass
class Client:
    id: int
    name: str
    phone: str = ""
    email: str = ""

    def get_display_name(self) -> str:
        return self.name

    def update_contacts(self, phone: str, email: str) -> None:
        self.phone, self.email = phone.strip(), email.strip()


@dataclass
class Equipment:
    id: int
    inventory_number: str
    name: str
    kind: str
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    room: Room | None = None

    def assign_to(self, room: Room | None) -> None:
        if self.room is not None and self in self.room.equipment:
            self.room.equipment.remove(self)
        self.room = room
        if room is not None and self not in room.equipment:
            room.equipment.append(self)

    def mark_for_maintenance(self) -> None:
        self.status = EquipmentStatus.MAINTENANCE

    def mark_available(self) -> None:
        self.status = EquipmentStatus.AVAILABLE


@dataclass
class Room:
    id: int
    name: str
    purpose: RoomPurpose
    hourly_rate: Decimal
    equipment: list[Equipment] = field(default_factory=list)
    sessions: list[RecordingSession] = field(default_factory=list, repr=False)

    def is_available(self, start: datetime, duration_minutes: int) -> bool:
        if duration_minutes <= 0:
            return False
        end = start + timedelta(minutes=duration_minutes)
        return all(
            session.status in {SessionStatus.CANCELLED, SessionStatus.FINISHED}
            or end <= session.start
            or start >= session.end
            for session in self.sessions
        )

    def calculate_cost(self, duration_minutes: int) -> Decimal:
        if duration_minutes <= 0:
            raise ValueError("Длительность должна быть больше нуля.")
        return (self.hourly_rate * duration_minutes / 60).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def add_equipment(self, item: Equipment) -> None:
        item.assign_to(self)


@dataclass
class Project:
    id: int
    title: str
    client: Client
    status: ProjectStatus = ProjectStatus.NEW
    created_at: date = field(default_factory=date.today)
    notes: str = ""
    sessions: list[RecordingSession] = field(default_factory=list)

    def add_session(self, session: RecordingSession) -> None:
        if session not in self.sessions:
            self.sessions.append(session)

    def change_status(self, status: ProjectStatus) -> None:
        self.status = status

    def get_total_duration(self) -> int:
        return sum(
            session.duration_minutes
            for session in self.sessions
            if session.status != SessionStatus.CANCELLED
        )


@dataclass
class RecordingSession:
    id: int
    start: datetime
    duration_minutes: int
    project: Project
    room: Room
    engineer: SoundEngineer
    status: SessionStatus = SessionStatus.PLANNED

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("Длительность должна быть положительной.")

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.duration_minutes)

    def change_status(self, status: SessionStatus) -> None:
        allowed = {
            SessionStatus.PLANNED: {SessionStatus.CONFIRMED, SessionStatus.CANCELLED},
            SessionStatus.CONFIRMED: {SessionStatus.FINISHED, SessionStatus.CANCELLED},
            SessionStatus.FINISHED: set(),
            SessionStatus.CANCELLED: set(),
        }
        if status not in allowed[self.status]:
            raise ValueError(f"Нельзя изменить статус «{self.status}» на «{status}».")
        self.status = status

    def confirm(self) -> None:
        self.change_status(SessionStatus.CONFIRMED)

    def cancel(self) -> None:
        self.change_status(SessionStatus.CANCELLED)

    def finish(self) -> None:
        self.change_status(SessionStatus.FINISHED)

    def calculate_cost(self) -> Decimal:
        return self.room.calculate_cost(self.duration_minutes)


@dataclass
class Employee(ABC):
    id: int
    full_name: str
    phone: str = ""
    email: str = ""

    def get_display_name(self) -> str:
        return self.full_name

    @abstractmethod
    def get_role(self) -> str:
        """Возвращает название роли конкретного сотрудника."""

    @abstractmethod
    def get_details(self) -> str:
        """Полиморфное описание сотрудника для таблицы."""


@dataclass
class SoundEngineer(Employee):
    specialization: str = ""
    sessions: list[RecordingSession] = field(default_factory=list, repr=False)

    def get_role(self) -> str:
        return "Звукорежиссёр"

    def get_details(self) -> str:
        return self.specialization or "Специализация не указана"

    def accept_session(self, session: RecordingSession) -> None:
        if session not in self.sessions:
            self.sessions.append(session)

    def is_available(self, start: datetime, duration_minutes: int) -> bool:
        end = start + timedelta(minutes=duration_minutes)
        return duration_minutes > 0 and all(
            session.status in {SessionStatus.CANCELLED, SessionStatus.FINISHED}
            or end <= session.start
            or start >= session.end
            for session in self.sessions
        )


@dataclass
class StudioAdministrator(Employee):
    def get_role(self) -> str:
        return "Администратор"

    def get_details(self) -> str:
        return "Работа с проектами и расписанием"

    def schedule_session(
        self,
        project: Project,
        room: Room,
        engineer: SoundEngineer,
        start: datetime,
        duration_minutes: int,
        session_id: int = 0,
    ) -> RecordingSession:
        if not room.is_available(start, duration_minutes):
            raise ValueError("Помещение уже занято в это время.")
        if not engineer.is_available(start, duration_minutes):
            raise ValueError("Звукорежиссёр уже занят в это время.")
        session = RecordingSession(session_id, start, duration_minutes, project, room, engineer)
        project.add_session(session)
        room.sessions.append(session)
        engineer.accept_session(session)
        return session

    def cancel_session(self, session: RecordingSession) -> None:
        session.cancel()


@dataclass
class Studio:
    name: str
    address: str = ""
    rooms: list[Room] = field(default_factory=list)
    clients: list[Client] = field(default_factory=list)
    employees: list[Employee] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)

    @property
    def equipment(self) -> list[Equipment]:
        return [item for room in self.rooms for item in room.equipment]

    @property
    def sessions(self) -> list[RecordingSession]:
        return [session for project in self.projects for session in project.sessions]

    def add_room(self, room: Room) -> None:
        self.rooms.append(room)

    def add_client(self, client: Client) -> None:
        self.clients.append(client)

    def add_employee(self, employee: Employee) -> None:
        self.employees.append(employee)

    def create_project(self, title: str, client: Client) -> Project:
        project = Project(len(self.projects) + 1, title, client)
        self.projects.append(project)
        return project

    def find_available_rooms(self, start: datetime, duration_minutes: int) -> list[Room]:
        return [room for room in self.rooms if room.is_available(start, duration_minutes)]
