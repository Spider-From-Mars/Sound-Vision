from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from studio_app.auth import AuthService
from studio_app.database import Database
from studio_app.models import SoundEngineer, StudioAdministrator
from studio_app.service import StudioService


@pytest.fixture
def service(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    yield StudioService(db.connection)
    db.close()


def seed(service):
    client_id = service.save("clients", {"name": "Клиент"})
    engineer_id = service.save(
        "employees", {"full_name": "Инженер", "role": "Звукорежиссёр", "specialization": "Запись"}
    )
    room_id = service.save("rooms", {"name": "Зал", "purpose": "Запись", "hourly_rate": 600000})
    project_id = service.save(
        "projects", {"title": "Альбом", "client_id": client_id, "status": "Новый", "notes": ""}
    )
    return client_id, engineer_id, room_id, project_id


def test_load_studio_creates_domain_objects_and_polymorphic_employees(service):
    seed(service)
    service.save("employees", {"full_name": "Администратор", "role": "Администратор"})

    studio = service.load_studio()

    assert studio.name == "Sound & Vision"
    assert isinstance(studio.employees[0], SoundEngineer)
    assert isinstance(studio.employees[1], StudioAdministrator)
    assert [employee.get_role() for employee in studio.employees] == [
        "Звукорежиссёр",
        "Администратор",
    ]
    assert studio.rooms[0].hourly_rate == Decimal(6000)


def test_schedule_checks_conflicts_and_calculates_cost(service):
    _client_id, engineer_id, room_id, project_id = seed(service)
    start = (datetime.now() + timedelta(days=2)).replace(second=0, microsecond=0)
    values = {
        "project_id": project_id,
        "room_id": room_id,
        "engineer_id": engineer_id,
        "starts_at": start.isoformat(timespec="minutes"),
        "duration_minutes": 90,
        "status": "Запланирован",
        "notes": "",
    }
    service.schedule(values.copy())
    assert service.rows("sessions")[0]["cost"] == 900000
    conflict = values | {"starts_at": (start + timedelta(minutes=30)).isoformat(timespec="minutes")}
    with pytest.raises(ValueError, match="Помещение уже занято"):
        service.schedule(conflict)


def test_crud_and_session_status(service):
    _client_id, engineer_id, room_id, project_id = seed(service)
    client_id = service.save("clients", {"name": "Старое имя"})
    service.save("clients", {"name": "Новое имя"}, client_id)
    assert service.get("clients", client_id)["name"] == "Новое имя"
    start = (datetime.now() + timedelta(days=2)).replace(second=0, microsecond=0)
    session_id = service.schedule(
        {
            "project_id": project_id,
            "room_id": room_id,
            "engineer_id": engineer_id,
            "starts_at": start.isoformat(timespec="minutes"),
            "duration_minutes": 60,
            "status": "Запланирован",
            "notes": "",
        }
    )
    service.change_session_status(session_id, "Подтверждён")
    assert service.get("sessions", session_id)["status"] == "Подтверждён"
    with pytest.raises(ValueError):
        service.change_session_status(session_id, "Запланирован")
    service.delete("clients", client_id)
    assert service.get("clients", client_id) is None


def test_local_authentication_stores_and_checks_password_hash(tmp_path):
    db = Database(tmp_path / "auth.sqlite3")
    auth = AuthService(db.connection)

    auth.register("studio-user", "long-password")

    assert auth.has_users()
    assert auth.authenticate("studio-user", "long-password")
    assert not auth.authenticate("studio-user", "wrong-password")
    db.close()
