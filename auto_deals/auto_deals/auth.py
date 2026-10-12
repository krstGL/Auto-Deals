import customtkinter as ctk
from tkinter import messagebox
import hmac
import re
import sqlite3

from .common import (
    ADMIN_OWNER_EMAIL,
    BannedAccountError,
    COLORS,
    DuplicateAccountError,
    generate_captcha,
    toggle_password_visibility,
)


class AuthenticationPages:
    # LOGIN / SIGN-UP WINDOW: builds the buyer and seller authentication form.
    def show_auth_screen(self, mode):
        self.set_auth_geometry()
        self.sidebar.grid_remove()
        self.main.grid_remove()
        if self.auth_frame is not None:
            self.auth_frame.destroy()

        self.auth_mode = mode
        self.auth_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["ivory"], corner_radius=0
        )
        self.auth_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.auth_frame.grid_columnconfigure(0, weight=1)
        self.auth_frame.grid_rowconfigure(0, weight=1)
        card_width = min(620, self.screen_width - 128)
        card = ctk.CTkFrame(
            self.auth_frame, width=card_width,
            fg_color=COLORS["card"], corner_radius=16,
            border_width=1, border_color=COLORS["border"]
        )
        card.grid(row=0, column=0, padx=18, pady=18)
        card.grid_columnconfigure(0, weight=1, minsize=card_width - 2)

        is_signup = mode == "signup"
        ctk.CTkLabel(
            card, text="Create your account" if is_signup else "Welcome back",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=COLORS["text"]
        ).grid(row=0, column=0, pady=(24, 12))

        self.auth_entries = {}
        self.password_visibility_buttons = {}
        fields = []
        if is_signup:
            fields.append(("Full name", "full_name", ""))
        fields.extend([
            ("Email address", "email", ""),
            ("Password", "password", "•"),
        ])
        if is_signup:
            fields.append(("Confirm password", "confirm_password", "•"))

        row = 2
        for label, key, mask in fields:
            ctk.CTkLabel(
                card, text=label, text_color=COLORS["text"],
                font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=row, column=0, sticky="w", padx=30, pady=(3, 2))
            row += 1
            if key in ("password", "confirm_password"):
                password_row = ctk.CTkFrame(card, fg_color="transparent")
                password_row.grid(
                    row=row, column=0, sticky="ew", padx=30, pady=(0, 3)
                )
                password_row.grid_columnconfigure(0, weight=1)
                entry = ctk.CTkEntry(
                    password_row, height=34, placeholder_text=label, show=mask,
                    fg_color=COLORS["ivory"], border_color=COLORS["border"],
                    text_color=COLORS["text"]
                )
                entry.grid(row=0, column=0, sticky="ew")
                visibility_button = ctk.CTkButton(
                    password_row, text="Show", width=64, height=34,
                    fg_color=COLORS["khaki"], hover_color=COLORS["olive"],
                    text_color=COLORS["text"]
                )
                visibility_button.grid(row=0, column=1, padx=(6, 0))
                visibility_button.configure(
                    command=lambda e=entry, b=visibility_button, m=mask:
                    toggle_password_visibility(e, b, m)
                )
                self.password_visibility_buttons[key] = visibility_button
            else:
                entry = ctk.CTkEntry(
                    card, height=34, placeholder_text=label, show=mask,
                    fg_color=COLORS["ivory"], border_color=COLORS["border"],
                    text_color=COLORS["text"]
                )
                entry.grid(
                    row=row, column=0, sticky="ew", padx=30, pady=(0, 3)
                )
            self.auth_entries[key] = entry
            row += 1

        if is_signup:
            ctk.CTkLabel(
                card, text="Account type", text_color=COLORS["text"],
                font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=row, column=0, sticky="w", padx=30, pady=(5, 2))
            row += 1
            self.account_type_menu = ctk.CTkOptionMenu(
                card, values=["Buyer", "Seller"], height=34,
                fg_color=COLORS["olive"], button_color=COLORS["olive_hover"]
            )
            self.account_type_menu.grid(
                row=row, column=0, sticky="ew", padx=30, pady=(0, 3)
            )
            row += 1

        ctk.CTkLabel(
            card, text="Human verification", text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=row, column=0, sticky="w", padx=30, pady=(5, 2))
        row += 1
        captcha_row = ctk.CTkFrame(card, fg_color="transparent")
        captcha_row.grid(row=row, column=0, sticky="ew", padx=30, pady=(0, 2))
        captcha_row.grid_columnconfigure(0, weight=1)
        self.captcha_prompt = ctk.CTkLabel(
            captcha_row, text="", text_color=COLORS["maroon"],
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.captcha_prompt.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            captcha_row, text="Refresh", width=75, height=28,
            fg_color=COLORS["khaki"], hover_color=COLORS["olive"],
            text_color=COLORS["text"], command=self.refresh_captcha
        ).grid(row=0, column=1, padx=(6, 0))
        row += 1
        self.captcha_entry = ctk.CTkEntry(
            card, height=32, placeholder_text="Enter the answer",
            fg_color=COLORS["ivory"], border_color=COLORS["border"],
            text_color=COLORS["text"]
        )
        self.captcha_entry.grid(row=row, column=0, sticky="ew", padx=30, pady=(0, 7))
        row += 1
        self.refresh_captcha()

        ctk.CTkButton(
            card, text="Create Account" if is_signup else "Log In",
            height=42, fg_color=COLORS["olive"], hover_color=COLORS["olive_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self.submit_auth(mode)
        ).grid(row=row, column=0, sticky="ew", padx=30, pady=(3, 5))
        row += 1
        ctk.CTkButton(
            card,
            text="Already have an account? Log in" if is_signup else "New here? Create an account",
            height=32, fg_color="transparent", hover_color=COLORS["khaki"],
            text_color=COLORS["olive"],
            command=lambda: self.show_auth_screen("login" if is_signup else "signup")
        ).grid(row=row, column=0, pady=(0, 18))

    # LOGIN / SIGN-UP WINDOW: refreshes its human-verification challenge.
    def refresh_captcha(self):
        challenge, self.captcha_answer = generate_captcha()
        self.captcha_prompt.configure(text=f"Solve: {challenge}")
        self.captcha_entry.delete(0, "end")

    # LOGIN / SIGN-UP WINDOW: displays validation errors to the user.
    def reject_auth(self, message):
        messagebox.showerror("Account", message, parent=self)
        self.refresh_captcha()

    # LOGIN / SIGN-UP WINDOW: handles account creation and sign-in actions.
    def submit_auth(self, mode):
        email = self.auth_entries["email"].get().strip().lower()
        password = self.auth_entries["password"].get()
        captcha_answer = self.captcha_entry.get().strip()
        if not hmac.compare_digest(
            captcha_answer.encode("utf-8"), self.captcha_answer.encode("utf-8")
        ):
            self.reject_auth("The CAPTCHA answer is incorrect. Please try the new challenge.")
            return

        if mode == "signup":
            full_name = self.auth_entries["full_name"].get().strip()
            confirm_password = self.auth_entries["confirm_password"].get()
            if email == ADMIN_OWNER_EMAIL:
                self.reject_auth("This email address is reserved for the administrator owner.")
                return
            if not full_name:
                self.reject_auth("Enter your full name.")
                return
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                self.reject_auth("Enter a valid email address.")
                return
            if len(password) < 8 or not password.strip():
                self.reject_auth("Choose a password with at least 8 characters.")
                return
            if password != confirm_password:
                self.reject_auth("The passwords do not match.")
                return
            try:
                role = self.account_type_menu.get().lower()
                account = self.account_store.register(full_name, email, password, role)
            except DuplicateAccountError:
                self.reject_auth("An account with that email already exists.")
                return
            except (sqlite3.Error, ValueError) as exc:
                self.reject_auth(f"Could not save the account: {exc}")
                return
        else:
            if not email or not password:
                self.reject_auth("Enter your email address and password.")
                return
            if email == ADMIN_OWNER_EMAIL:
                self.open_admin_window()
                return
            try:
                account = self.account_store.authenticate(email, password)
            except BannedAccountError:
                self.reject_auth("This account has been banned. Contact the administrator.")
                return
            except sqlite3.Error as exc:
                self.reject_auth(f"Could not access the local account database: {exc}")
                return
            if account is None:
                self.reject_auth("The email address or password is incorrect.")
                return
            if account["role"] == "admin":
                self.reject_auth("Administrator accounts must use the owner login.")
                return

        self.current_user = account
        self.set_seller_tools_visible(account["role"] == "seller")
        self.account_button.configure(text=f'{account["full_name"].split()[0]}  ▾')
        self.auth_frame.destroy()
        self.auth_frame = None
        window_width = min(1440, self.screen_width - 80)
        window_height = min(850, self.screen_height - 100)
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(min(1050, window_width), min(680, window_height))
        self.sidebar.grid()
        self.main.grid()
        self.show_page("Dashboard")