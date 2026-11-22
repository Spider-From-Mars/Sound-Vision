from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3


class AuthService:
    ITERATIONS = 310_000

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    def has_users(self) -> bool:
        return self.db.execute("SELECT EXISTS(SELECT 1 FROM users)").fetchone()[0] == 1

    def register(self, username: str, password: str) -> None:
        username = username.strip()
        if len(username) < 3:
            raise ValueError("Имя пользователя должно содержать не менее 3 символов.")
        if len(password) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов.")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self.ITERATIONS)
        try:
            self.db.execute(
                "INSERT INTO users(username,salt,password_hash) VALUES(?,?,?)",
                (username, salt, digest),
            )
            self.db.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("Пользователь с таким именем уже существует.") from exc

    def authenticate(self, username: str, password: str) -> bool:
        row = self.db.execute(
            "SELECT salt,password_hash FROM users WHERE username=?", (username.strip(),)
        ).fetchone()
        if row is None:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), row["salt"], self.ITERATIONS)
        return hmac.compare_digest(candidate, row["password_hash"])
