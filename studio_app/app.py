"""Точка входа в Tkinter-приложение."""

from __future__ import annotations

import tkinter as tk

from .auth import AuthService
from .database import Database
from .service import StudioService
from .ui import LoginDialog, MainWindow


def main() -> None:
    database = Database()
    root = tk.Tk()
    root.withdraw()
    login = LoginDialog(root, AuthService(database.connection))
    root.wait_window(login)
    if login.username is None:
        database.close()
        root.destroy()
        return
    MainWindow(root, StudioService(database.connection), login.username)
    root.deiconify()
    root.protocol("WM_DELETE_WINDOW", lambda: (database.close(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
