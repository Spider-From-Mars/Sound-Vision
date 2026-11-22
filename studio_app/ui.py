"""Окна и формы Tkinter приложения."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from .auth import AuthService
from .service import StudioService

TABLES = {
    "clients": (
        "Клиенты",
        [
            ("name", "Имя / название", "text"),
            ("phone", "Телефон", "text"),
            ("email", "Электронная почта", "text"),
            ("notes", "Заметки", "text"),
        ],
    ),
    "employees": (
        "Сотрудники",
        [
            ("full_name", "ФИО", "text"),
            ("role", "Роль", ["Звукорежиссёр", "Администратор"]),
            ("phone", "Телефон", "text"),
            ("email", "Электронная почта", "text"),
            ("specialization", "Специализация", "text"),
        ],
    ),
    "rooms": (
        "Помещения",
        [
            ("name", "Название", "text"),
            ("purpose", "Назначение", ["Запись", "Сведение", "Репетиционная", "Универсальная"]),
            ("hourly_rate", "Цена за час (₸)", "money"),
        ],
    ),
    "equipment": (
        "Оборудование",
        [
            ("inventory_number", "Инвентарный номер", "text"),
            ("name", "Название", "text"),
            ("kind", "Тип", "text"),
            ("status", "Статус", ["Доступно", "На обслуживании"]),
            ("room_id", "Помещение", "room"),
        ],
    ),
    "projects": (
        "Проекты",
        [
            ("title", "Название", "text"),
            ("client_id", "Клиент", "client"),
            ("status", "Статус", ["Новый", "В работе", "На паузе", "Завершён"]),
            ("notes", "Заметки", "text"),
        ],
    ),
    "sessions": (
        "Расписание",
        [
            ("project_id", "Проект", "project"),
            ("room_id", "Помещение", "room"),
            ("engineer_id", "Звукорежиссёр", "engineer"),
            ("starts_at", "Начало (ГГГГ-ММ-ДД ЧЧ:ММ)", "datetime"),
            ("duration_minutes", "Длительность (мин.)", "integer"),
            ("status", "Статус", ["Запланирован", "Подтверждён", "Завершён", "Отменён"]),
            ("notes", "Заметки", "text"),
        ],
    ),
}

HEADERS = {
    "clients": [
        ("id", "ID"),
        ("name", "Имя / название"),
        ("phone", "Телефон"),
        ("email", "Электронная почта"),
    ],
    "employees": [
        ("id", "ID"),
        ("full_name", "ФИО"),
        ("role", "Роль"),
        ("specialization", "Специализация / обязанности"),
        ("phone", "Телефон"),
        ("email", "Электронная почта"),
    ],
    "rooms": [
        ("id", "ID"),
        ("name", "Название"),
        ("purpose", "Назначение"),
        ("hourly_rate", "Цена/час (₸)"),
    ],
    "equipment": [
        ("id", "ID"),
        ("inventory_number", "Инв. номер"),
        ("name", "Название"),
        ("kind", "Тип"),
        ("status", "Статус"),
        ("room", "Помещение"),
    ],
    "projects": [("id", "ID"), ("title", "Проект"), ("client", "Клиент"), ("status", "Статус")],
    "sessions": [
        ("id", "ID"),
        ("starts_at", "Начало"),
        ("project", "Проект"),
        ("room", "Помещение"),
        ("engineer", "Звукорежиссёр"),
        ("duration_minutes", "Мин."),
        ("status", "Статус"),
        ("cost", "Стоимость (₸)"),
    ],
}


class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, auth: AuthService) -> None:
        super().__init__(parent)
        self.auth = auth
        self.username: str | None = None
        self.register_mode = not auth.has_users()
        self.title("Sound & Vision — вход")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        frame = ttk.Frame(self, padding=22)
        frame.grid(sticky="nsew")
        ttk.Label(
            frame, text="SOUND & VISION", font=("TkDefaultFont", 18, "bold"), foreground="#1764c0"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 6))
        self.heading = ttk.Label(frame)
        self.heading.grid(row=1, column=0, columnspan=2, pady=(0, 14))
        ttk.Label(frame, text="Имя пользователя:").grid(row=2, column=0, sticky="w", pady=5)
        self.user_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.user_var, width=28).grid(row=2, column=1, pady=5)
        ttk.Label(frame, text="Пароль:").grid(row=3, column=0, sticky="w", pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show="•", width=28).grid(
            row=3, column=1, pady=5
        )
        self.confirm_label = ttk.Label(frame, text="Повтор пароля:")
        self.confirm_var = tk.StringVar()
        self.confirm_entry = ttk.Entry(frame, textvariable=self.confirm_var, show="•", width=28)
        self.confirm_label.grid(row=4, column=0, sticky="w", pady=5)
        self.confirm_entry.grid(row=4, column=1, pady=5)
        self.error = ttk.Label(frame, foreground="#b42318", wraplength=340)
        self.error.grid(row=5, column=0, columnspan=2, pady=5)
        self.submit_button = ttk.Button(frame, command=self.submit)
        self.submit_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.switch_button = ttk.Button(frame, command=self.toggle_mode)
        self.switch_button.grid(row=7, column=0, columnspan=2, sticky="ew")
        self._render_mode()
        self.bind("<Return>", lambda _event: self.submit())
        self.grab_set()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 70}")
        self.lift()
        self.focus_force()

    def _render_mode(self) -> None:
        self.heading.configure(
            text="Создайте локальную учётную запись" if self.register_mode else "Войдите в систему"
        )
        self.submit_button.configure(text="Зарегистрироваться" if self.register_mode else "Войти")
        self.switch_button.configure(
            text="Уже есть аккаунт? Войти" if self.register_mode else "Регистрация"
        )
        state = "normal" if self.register_mode else "disabled"
        self.confirm_entry.configure(state=state)
        self.confirm_label.configure(state=state)

    def toggle_mode(self) -> None:
        self.register_mode = not self.register_mode
        self.error.configure(text="")
        self._render_mode()

    def submit(self) -> None:
        username, password = self.user_var.get().strip(), self.password_var.get()
        try:
            if self.register_mode:
                if password != self.confirm_var.get():
                    raise ValueError("Пароли не совпадают.")
                self.auth.register(username, password)
            elif not self.auth.authenticate(username, password):
                raise ValueError("Неверное имя пользователя или пароль.")
        except ValueError as exc:
            self.error.configure(text=str(exc))
            return
        self.username = username
        self.destroy()

    def _cancel(self) -> None:
        self.username = None
        self.destroy()


class RecordDialog(tk.Toplevel):
    def __init__(
        self, parent: tk.Misc, service: StudioService, table: str, record: sqlite3.Row | None = None
    ) -> None:
        super().__init__(parent)
        self.service, self.table, self.record = service, table, record
        self.result: dict[str, Any] | None = None
        title, fields = TABLES[table]
        self.title(("Редактировать — " if record else "Добавить — ") + title.lower())
        self.resizable(False, True)
        self.transient(parent)
        self.variables: dict[str, tk.StringVar] = {}
        self.choice_maps: dict[str, dict[str, int | None]] = {}
        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")
        for row_index, (key, label, kind) in enumerate(fields):
            ttk.Label(frame, text=label + ":").grid(
                row=row_index, column=0, sticky="w", padx=(0, 12), pady=5
            )
            value = record[key] if record is not None and key in record.keys() else ""  # noqa: SIM118
            var = tk.StringVar(value=str(value))
            self.variables[key] = var
            if isinstance(kind, list):
                widget = ttk.Combobox(
                    frame, textvariable=var, values=kind, state="readonly", width=34
                )
                if not value:
                    widget.current(0)
            elif kind in {"room", "client", "project", "engineer"}:
                items = self._choice_items(kind)
                labels = [label for label, _object_id in items]
                self.choice_maps[key] = {label: object_id for label, object_id in items}
                widget = ttk.Combobox(
                    frame, textvariable=var, values=labels, state="readonly", width=34
                )
                current_id = int(value) if value not in (None, "") else None
                selected = next(
                    (label for label, object_id in items if object_id == current_id), ""
                )
                if selected:
                    var.set(selected)
                elif labels:
                    widget.current(0)
            else:
                if key == "starts_at" and not value:
                    var.set(
                        datetime.now().replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
                    )
                widget = ttk.Entry(frame, textvariable=var, width=37)
            widget.grid(row=row_index, column=1, sticky="ew", pady=5)
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side="left", padx=4)
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="left", padx=4)
        self.bind("<Return>", lambda _event: self.save())
        self.grab_set()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 45}+{parent.winfo_rooty() + 45}")

    def _choice_items(self, kind: str) -> list[tuple[str, int | None]]:
        if kind == "room":
            rooms = [(row["name"], row["id"]) for row in self.service.choices("rooms")]
            return [("— без помещения —", None), *rooms] if self.table == "equipment" else rooms
        if kind == "client":
            return [(row["name"], row["id"]) for row in self.service.choices("clients")]
        if kind == "project":
            return [(row["title"], row["id"]) for row in self.service.choices("projects")]
        return [
            (row["full_name"], row["id"])
            for row in self.service.choices("employees", "WHERE role='Звукорежиссёр'")
        ]

    def save(self) -> None:
        values: dict[str, Any] = {}
        for key, _label, kind in TABLES[self.table][1]:
            raw = self.variables[key].get().strip()
            if key in {"name", "full_name", "title", "inventory_number", "kind"} and not raw:
                messagebox.showwarning(
                    "Проверьте форму", "Заполните обязательные поля.", parent=self
                )
                return
            try:
                if isinstance(kind, list):
                    values[key] = raw
                elif kind in {"room", "client", "project", "engineer"}:
                    object_id = self.choice_maps[key].get(raw)
                    if object_id is None and not (self.table == "equipment" and key == "room_id"):
                        raise ValueError("Сначала создайте необходимые связанные записи.")
                    values[key] = object_id
                elif kind == "integer":
                    values[key] = int(raw)
                elif kind == "money":
                    values[key] = round(float(raw.replace(",", ".")) * 100)
                elif kind == "datetime":
                    values[key] = datetime.strptime(raw, "%Y-%m-%d %H:%M").isoformat(
                        timespec="minutes"
                    )
                else:
                    values[key] = raw
            except (ValueError, KeyError) as exc:
                messagebox.showwarning(
                    "Проверьте форму", str(exc) or "Проверьте введённые данные.", parent=self
                )
                return
        try:
            if self.table == "sessions":
                object_id = int(self.record["id"]) if self.record else None
                self.service.schedule(values, object_id)
            else:
                self.service.save(
                    self.table, values, int(self.record["id"]) if self.record else None
                )
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Не удалось сохранить", str(exc), parent=self)
            return
        self.result = values
        self.destroy()


class AboutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title("О программе — Sound & Vision")
        self.resizable(False, False)
        self.transient(parent)
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Sound & Vision", font=("TkDefaultFont", 18, "bold")).pack(
            pady=(0, 10)
        )
        canvas = tk.Canvas(body, width=260, height=90, background="#17243b", highlightthickness=0)
        canvas.pack(pady=6)
        canvas.create_oval(22, 20, 72, 70, outline="#7dd3fc", width=4)
        canvas.create_oval(37, 35, 57, 55, fill="#7dd3fc", outline="")
        canvas.create_line(84, 45, 110, 45, fill="#7dd3fc", width=3)
        canvas.create_text(185, 45, text="STUDIO", fill="white", font=("TkDefaultFont", 16, "bold"))
        ttk.Label(
            body,
            text="Программа для управления студией звукозаписи.\nКлиенты, сотрудники, проекты, оборудование и расписание.\n\nPython · Tkinter · SQLite",
            justify="center",
        ).pack(pady=10)
        ttk.Button(body, text="Закрыть", command=self.destroy).pack(pady=(4, 0))
        self.transient(parent)
        self.grab_set()


class MainWindow:
    def __init__(self, root: tk.Tk, service: StudioService, username: str = "") -> None:
        self.root, self.service, self.username = root, service, username
        self.root.title("Sound & Vision — управление студией")
        self.root.geometry("1120x690")
        self.root.minsize(850, 520)
        self.studio = service.load_studio()
        self.trees: dict[str, ttk.Treeview] = {}
        self._make_menu()
        outer = ttk.Frame(root, padding=14)
        outer.pack(fill="both", expand=True)
        menu_bar = ttk.Frame(outer)
        menu_bar.pack(fill="x", pady=(0, 8))
        window_menu_button = tk.Menubutton(menu_bar, text="Меню", relief=tk.RAISED)
        window_menu = tk.Menu(window_menu_button, tearoff=False)
        window_menu.add_command(label="О программе", command=lambda: AboutDialog(self.root))
        window_menu.add_separator()
        window_menu.add_command(label="Выход", command=self.root.destroy)
        window_menu_button.configure(menu=window_menu)
        window_menu_button.pack(side="left")
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Sound & Vision", font=("TkDefaultFont", 20, "bold")).pack(
            side="left"
        )
        ttk.Label(
            header, text=f"Студия звукозаписи · {username}" if username else "Студия звукозаписи"
        ).pack(side="right")
        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        for table, (title, _fields) in TABLES.items():
            self._make_tab(table, title)
        self.refresh_all()

    def _make_menu(self) -> None:
        menu = tk.Menu(self.root)
        menu.add_command(label="О программе", command=lambda: AboutDialog(self.root))
        menu.add_command(label="Выход", command=self.root.destroy)
        self.root.configure(menu=menu)

    def _make_tab(self, table: str, title: str) -> None:
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text=title)
        bar = ttk.Frame(page)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Добавить", command=lambda t=table: self.add(t)).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(bar, text="Изменить", command=lambda t=table: self.edit(t)).pack(
            side="left", padx=5
        )
        ttk.Button(bar, text="Удалить", command=lambda t=table: self.delete(t)).pack(
            side="left", padx=5
        )
        if table == "sessions":
            ttk.Button(bar, text="Изменить статус", command=self.change_status).pack(
                side="left", padx=5
            )
        headers = HEADERS[table]
        tree = ttk.Treeview(
            page, columns=[key for key, _ in headers], show="headings", selectmode="browse"
        )
        for key, label in headers:
            tree.heading(key, text=label)
            tree.column(
                key, width=130 if key not in {"notes", "id"} else 70, minwidth=60, anchor="w"
            )
        y_scroll = ttk.Scrollbar(page, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(page, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.pack(side="top", fill="both", expand=True)
        x_scroll.pack(side="bottom", fill="x")
        y_scroll.place(relx=1, rely=0, relheight=1, anchor="ne")
        tree.bind("<Double-1>", lambda _event, t=table: self.edit(t))
        self.trees[table] = tree

    def _display_values(self, table: str, row: sqlite3.Row) -> tuple[Any, ...]:
        if table == "employees":
            employee = next((e for e in self.studio.employees if e.id == row["id"]), None)
            if employee:
                return (
                    row["id"],
                    employee.get_display_name(),
                    employee.get_role(),
                    employee.get_details(),
                    row["phone"],
                    row["email"],
                )
        values = []
        for key, _label in HEADERS[table]:
            value = row[key]
            if key == "hourly_rate" or key == "cost":
                value = f"{value / 100:,.2f}".replace(",", " ")
            values.append(value if value is not None else "—")
        return tuple(values)

    def refresh(self, table: str) -> None:
        self.studio = self.service.load_studio()
        tree = self.trees[table]
        tree.delete(*tree.get_children())
        for row in self.service.rows(table):
            tree.insert("", "end", iid=str(row["id"]), values=self._display_values(table, row))

    def refresh_all(self) -> None:
        self.studio = self.service.load_studio()
        for table in TABLES:
            tree = self.trees[table]
            tree.delete(*tree.get_children())
            for row in self.service.rows(table):
                tree.insert("", "end", iid=str(row["id"]), values=self._display_values(table, row))

    def selected_id(self, table: str) -> int | None:
        selection = self.trees[table].selection()
        return int(selection[0]) if selection else None

    def add(self, table: str) -> None:
        if table == "projects" and not self.service.choices("clients"):
            messagebox.showinfo(
                "Сначала клиент", "Перед созданием проекта добавьте клиента.", parent=self.root
            )
            return
        if table == "sessions" and (
            not self.service.choices("projects")
            or not self.service.choices("rooms")
            or not self.service.choices("employees", "WHERE role='Звукорежиссёр'")
        ):
            messagebox.showinfo(
                "Недостаточно данных",
                "Добавьте проект, помещение и звукорежиссёра.",
                parent=self.root,
            )
            return
        dialog = RecordDialog(self.root, self.service, table)
        self.root.wait_window(dialog)
        if dialog.result is not None:
            self.refresh_all()

    def edit(self, table: str) -> None:
        object_id = self.selected_id(table)
        if object_id is None:
            messagebox.showinfo(
                "Выберите запись", "Сначала выделите строку в таблице.", parent=self.root
            )
            return
        dialog = RecordDialog(self.root, self.service, table, self.service.get(table, object_id))
        self.root.wait_window(dialog)
        if dialog.result is not None:
            self.refresh_all()

    def delete(self, table: str) -> None:
        object_id = self.selected_id(table)
        if object_id is None:
            messagebox.showinfo(
                "Выберите запись", "Сначала выделите строку в таблице.", parent=self.root
            )
            return
        values = self.trees[table].item(str(object_id), "values")
        name = values[1] if len(values) > 1 else str(object_id)
        if not messagebox.askyesno("Подтверждение", f"Удалить запись «{name}»?", parent=self.root):
            return
        try:
            self.service.delete(table, object_id)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Запись используется",
                "Сначала удалите связанные проекты или сеансы.",
                parent=self.root,
            )
            return
        self.refresh_all()

    def change_status(self) -> None:
        session_id = self.selected_id("sessions")
        if session_id is None:
            messagebox.showinfo(
                "Выберите сеанс", "Выделите сеанс в таблице расписания.", parent=self.root
            )
            return
        row = self.service.get("sessions", session_id)
        next_statuses = {
            "Запланирован": ["Подтверждён", "Отменён"],
            "Подтверждён": ["Завершён", "Отменён"],
            "Завершён": [],
            "Отменён": [],
        }[row["status"]]
        if not next_statuses:
            messagebox.showinfo(
                "Статус", "Для этого сеанса переходов больше нет.", parent=self.root
            )
            return
        status = simpledialog.askstring(
            "Статус сеанса", "Доступно: " + ", ".join(next_statuses), parent=self.root
        )
        if status not in next_statuses:
            if status:
                messagebox.showwarning(
                    "Статус не изменён", "Выберите один из доступных статусов.", parent=self.root
                )
            return
        try:
            self.service.change_session_status(session_id, status)
        except ValueError as exc:
            messagebox.showerror("Статус не изменён", str(exc), parent=self.root)
        self.refresh_all()
