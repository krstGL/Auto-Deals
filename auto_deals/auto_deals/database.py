from contextlib import contextmanager
from pathlib import Path
import sqlite3


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "auto_deals.db"


class Database:
    def __init__(self, path=DEFAULT_DATABASE_PATH):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    email TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    role TEXT NOT NULL DEFAULT 'buyer'
                )
                """
            )
            account_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(accounts)")
            }
            if "role" not in account_columns:
                connection.execute(
                    "ALTER TABLE accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'buyer'"
                )
            for column in ("phone_number", "location", "profile_photo"):
                if column not in account_columns:
                    connection.execute(
                        f"ALTER TABLE accounts ADD COLUMN {column} "
                        "TEXT NOT NULL DEFAULT ''"
                    )
            if "is_banned" not in account_columns:
                connection.execute(
                    "ALTER TABLE accounts ADD COLUMN is_banned "
                    "INTEGER NOT NULL DEFAULT 0"
                )
            connection.execute("DROP INDEX IF EXISTS accounts_username_unique")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS car_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    year TEXT NOT NULL,
                    price TEXT NOT NULL,
                    mileage TEXT NOT NULL,
                    location TEXT NOT NULL,
                    transmission TEXT NOT NULL,
                    fuel TEXT NOT NULL,
                    body TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    photo TEXT NOT NULL
                )
                """
            )
            listing_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(car_listings)")
            }
            if "seller_email" not in listing_columns:
                connection.execute(
                    "ALTER TABLE car_listings ADD COLUMN seller_email "
                    "TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL,
                    buyer_email TEXT NOT NULL,
                    seller_email TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (listing_id, buyer_email, seller_email)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    sender_email TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS messages_conversation_id_idx "
                "ON messages (conversation_id, id)"
            )

    def save_listing(self, car):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO car_listings (
                    model, year, price, mileage, location, transmission,
                    fuel, body, condition, description, photo, seller_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    car["model"], car["year"], car["price"], car["mileage"],
                    car["location"], car["transmission"], car["fuel"],
                    car["body"], car["condition"], car["description"],
                    car["photo"], car.get("seller_email", ""),
                ),
            )
            return cursor.lastrowid

    def load_listings(self):
        with self.connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, model, year, price, mileage, location, transmission,
                       fuel, body, condition, description, photo, seller_email
                FROM car_listings
                ORDER BY id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_listing(self, listing_id):
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM car_listings WHERE id = ?", (listing_id,)
            )
            return cursor.rowcount == 1
