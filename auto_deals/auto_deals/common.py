import customtkinter as ctk
import hashlib
import hmac
import secrets
import sqlite3

from .database import Database

# Auto Deals GUI prototype
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

COLORS = {
    "maroon": "#641E2B",
    "maroon_hover": "#4E1721",
    "khaki": "#C3B091",
    "olive": "#667744",
    "olive_hover": "#505F32",
    "red": "#C0392B",
    "red_hover": "#962D22",
    "ivory": "#F7F3EA",
    "card": "#FFFCF5",
    "text": "#292725",
    "muted": "#777168",
    "border": "#E4D9C6",
    "pale_green": "#E9EEDD",
    "gold": "#D6AD55",
}

PASSWORD_HASH_ITERATIONS = 310_000
ADMIN_OWNER_EMAIL = "kristgelo238@gmail.com"


class DuplicateAccountError(Exception):
    pass


class BannedAccountError(Exception):
    pass


class AccountStore:
    def __init__(self, database_path):
        self.database = (
            database_path
            if isinstance(database_path, Database)
            else Database(database_path)
        )
        self.database_path = self.database.path
        self.database.initialize()

    def register(self, full_name, email, password, role="buyer"):
        if role not in ("buyer", "seller"):
            raise ValueError("Regular account role must be buyer or seller.")
        if email.strip().lower() == ADMIN_OWNER_EMAIL:
            raise ValueError("This email address is reserved for the administrator owner.")
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
        )
        try:
            with self.database.connect() as connection:
                connection.execute(
                    "INSERT INTO accounts (email, full_name, password_salt, password_hash, role) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (email, full_name, salt, password_hash, role),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateAccountError from exc
        return {
            "email": email,
            "full_name": full_name,
            "role": role,
            "phone_number": "",
            "location": "",
            "profile_photo": "",
        }

    def authenticate(self, email, password):
        with self.database.connect() as connection:
            account = connection.execute(
                "SELECT full_name, password_salt, password_hash, role, "
                "phone_number, location, profile_photo, is_banned "
                "FROM accounts WHERE email = ?",
                (email,),
            ).fetchone()
        if account is None:
            return None
        (
            full_name, salt, password_hash, role, phone_number, location,
            profile_photo, is_banned,
        ) = account
        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
        )
        if not hmac.compare_digest(password_hash, candidate_hash):
            return None
        if is_banned:
            raise BannedAccountError("This account has been banned.")
        return {
            "email": email,
            "full_name": full_name,
            "role": role,
            "phone_number": phone_number,
            "location": location,
            "profile_photo": profile_photo,
        }

    def update_profile(
        self, old_email, email, full_name, phone_number, location, profile_photo
    ):
        old_email = old_email.strip().lower()
        email = email.strip().lower()
        if old_email == ADMIN_OWNER_EMAIL and email != ADMIN_OWNER_EMAIL:
            raise ValueError("The administrator owner's email address cannot be changed.")
        with self.database.connect() as connection:
            owner = connection.execute(
                "SELECT role FROM accounts WHERE email = ?", (old_email,)
            ).fetchone()
            if owner and owner[0] == "admin" and email != ADMIN_OWNER_EMAIL:
                raise ValueError(
                    "The administrator owner's email address cannot be changed."
                )
            cursor = connection.execute(
                "UPDATE accounts SET email = ?, full_name = ?, "
                "phone_number = ?, location = ?, profile_photo = ? WHERE email = ?",
                (
                    email, full_name, phone_number, location, profile_photo,
                    old_email
                ),
            )
            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError("The account profile could not be found.")
            connection.execute(
                "UPDATE car_listings SET seller_email = ? WHERE seller_email = ?",
                (email, old_email),
            )

    def register_initial_admin(self, full_name, email, password):
        email = email.strip().lower()
        if email != ADMIN_OWNER_EMAIL:
            raise ValueError("Only the configured administrator owner can be registered.")
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
        )
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM accounts WHERE email = ? AND role = 'admin'",
                (ADMIN_OWNER_EMAIL,),
            ).fetchone():
                raise DuplicateAccountError("An administrator account already exists.")
            owner_account = connection.execute(
                "SELECT 1 FROM accounts WHERE email = ?",
                (ADMIN_OWNER_EMAIL,),
            ).fetchone()
            if owner_account:
                connection.execute(
                    "UPDATE accounts SET full_name = ?, password_salt = ?, "
                    "password_hash = ?, role = 'admin' WHERE email = ?",
                    (full_name, salt, password_hash, ADMIN_OWNER_EMAIL),
                )
                return {
                    "email": ADMIN_OWNER_EMAIL,
                    "full_name": full_name,
                    "role": "admin",
                }
            try:
                connection.execute(
                    "INSERT INTO accounts (email, full_name, password_salt, password_hash, role) "
                    "VALUES (?, ?, ?, ?, 'admin')",
                    (email, full_name, salt, password_hash),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAccountError from exc
        return {"email": email, "full_name": full_name, "role": "admin"}

    def has_admin(self):
        with self.database.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM accounts WHERE email = ? AND role = 'admin'",
                (ADMIN_OWNER_EMAIL,),
            ).fetchone() is not None

    def role_counts(self):
        counts = {"buyer": 0, "seller": 0, "admin": 0}
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT role, COUNT(*) FROM accounts GROUP BY role"
            ).fetchall()
        counts.update(dict(rows))
        return counts

    def list_accounts(self):
        with self.database.connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT email, full_name, role, is_banned
                FROM accounts
                ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END,
                         full_name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def set_banned(self, email, banned):
        email = email.strip().lower()
        with self.database.connect() as connection:
            account = connection.execute(
                "SELECT role FROM accounts WHERE email = ?", (email,)
            ).fetchone()
            if account is None:
                raise ValueError("The selected account no longer exists.")
            if account[0] == "admin" or email == ADMIN_OWNER_EMAIL:
                raise ValueError("Administrator accounts cannot be banned.")
            cursor = connection.execute(
                "UPDATE accounts SET is_banned = ? WHERE email = ?",
                (int(banned), email),
            )
            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError("The selected account could not be updated.")
            if not banned:
                return []
            listing_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM car_listings WHERE seller_email = ?",
                    (email,),
                ).fetchall()
            ]
            connection.execute(
                "DELETE FROM car_listings WHERE seller_email = ?", (email,)
            )
            return listing_ids


class CarListingStore:
    def __init__(self, database_path):
        self.database = (
            database_path
            if isinstance(database_path, Database)
            else Database(database_path)
        )
        self.database_path = self.database.path
        self.database.initialize()

    def add(self, car):
        return self.database.save_listing(car)

    def list_all(self):
        return self.database.load_listings()

    def delete(self, listing_id):
        return self.database.delete_listing(listing_id)


class MessagingStore:
    def __init__(self, database_path):
        self.database = (
            database_path
            if isinstance(database_path, Database)
            else Database(database_path)
        )
        self.database.initialize()

    def start_conversation(self, listing_id, buyer_email):
        buyer_email = buyer_email.strip().lower()
        with self.database.connect() as connection:
            buyer = connection.execute(
                "SELECT role, is_banned FROM accounts WHERE email = ?",
                (buyer_email,),
            ).fetchone()
            if buyer is None or buyer[0] != "buyer" or buyer[1]:
                raise ValueError("Only an active buyer can contact a seller.")
            listing = connection.execute(
                "SELECT seller_email, model, year FROM car_listings WHERE id = ?",
                (listing_id,),
            ).fetchone()
            if listing is None:
                raise ValueError("This vehicle listing is no longer available.")
            seller_email = listing[0].strip().lower()
            if not seller_email:
                raise ValueError(
                    "The seller cannot be contacted for this older listing."
                )
            if seller_email == buyer_email:
                raise ValueError("You cannot message yourself about your own listing.")
            seller = connection.execute(
                "SELECT role, is_banned FROM accounts WHERE email = ?",
                (seller_email,),
            ).fetchone()
            if seller is None or seller[0] != "seller" or seller[1]:
                raise ValueError("This listing's seller is unavailable.")
            connection.execute(
                """
                INSERT INTO conversations (listing_id, buyer_email, seller_email)
                VALUES (?, ?, ?)
                ON CONFLICT (listing_id, buyer_email, seller_email) DO NOTHING
                """,
                (listing_id, buyer_email, seller_email),
            )
            conversation = connection.execute(
                """
                SELECT id FROM conversations
                WHERE listing_id = ? AND buyer_email = ? AND seller_email = ?
                """,
                (listing_id, buyer_email, seller_email),
            ).fetchone()
            return conversation[0]

    def list_conversations(self, user_email):
        user_email = user_email.strip().lower()
        with self.database.connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT c.id, c.listing_id, c.buyer_email, c.seller_email,
                       COALESCE(a.full_name, c.seller_email) AS seller_name,
                       COALESCE(b.full_name, c.buyer_email) AS buyer_name,
                       COALESCE(l.model, 'Removed listing') AS model,
                       COALESCE(l.year, '') AS year,
                       (SELECT m.body FROM messages m
                        WHERE m.conversation_id = c.id
                        ORDER BY m.id DESC LIMIT 1) AS last_message,
                       (SELECT m.created_at FROM messages m
                        WHERE m.conversation_id = c.id
                        ORDER BY m.id DESC LIMIT 1) AS last_message_at
                FROM conversations c
                LEFT JOIN accounts a ON a.email = c.seller_email
                LEFT JOIN accounts b ON b.email = c.buyer_email
                LEFT JOIN car_listings l ON l.id = c.listing_id
                WHERE c.buyer_email = ? OR c.seller_email = ?
                ORDER BY COALESCE(last_message_at, c.created_at) DESC, c.id DESC
                """,
                (user_email, user_email),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_messages(self, conversation_id, user_email):
        user_email = user_email.strip().lower()
        with self.database.connect() as connection:
            participant = connection.execute(
                """
                SELECT 1 FROM conversations
                WHERE id = ? AND (buyer_email = ? OR seller_email = ?)
                """,
                (conversation_id, user_email, user_email),
            ).fetchone()
            if participant is None:
                raise ValueError("You are not a participant in this conversation.")
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, sender_email, body, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id
                """,
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def send_message(self, conversation_id, sender_email, body):
        sender_email = sender_email.strip().lower()
        body = body.strip()
        if not body:
            raise ValueError("Enter a message before sending.")
        if len(body) > 2000:
            raise ValueError("Messages must be 2,000 characters or fewer.")
        with self.database.connect() as connection:
            participant = connection.execute(
                """
                SELECT 1 FROM conversations
                WHERE id = ? AND (buyer_email = ? OR seller_email = ?)
                """,
                (conversation_id, sender_email, sender_email),
            ).fetchone()
            if participant is None:
                raise ValueError("You are not a participant in this conversation.")
            account = connection.execute(
                "SELECT is_banned FROM accounts WHERE email = ?",
                (sender_email,),
            ).fetchone()
            if account is None or account[0]:
                raise ValueError("This account is unavailable for messaging.")
            cursor = connection.execute(
                """
                INSERT INTO messages (conversation_id, sender_email, body)
                VALUES (?, ?, ?)
                """,
                (conversation_id, sender_email, body),
            )
            return cursor.lastrowid


def generate_captcha():
    left = secrets.randbelow(19) + 2
    right = secrets.randbelow(19) + 2
    operator = secrets.choice(("+", "-"))
    if operator == "-":
        left, right = max(left, right), min(left, right)
        answer = left - right
    else:
        answer = left + right
    return f"{left} {operator} {right} = ?", str(answer)


def toggle_password_visibility(entry, button, masked_character):
    show_password = button.cget("text") == "Show"
    entry.configure(show="" if show_password else masked_character)
    button.configure(text="Hide" if show_password else "Show")
