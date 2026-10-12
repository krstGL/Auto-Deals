import customtkinter as ctk
from tkinter import messagebox
import hmac
import re
import sqlite3

from .common import (
    ADMIN_OWNER_EMAIL,
    BannedAccountError,
    CarListingStore,
    COLORS,
    DuplicateAccountError,
    generate_captcha,
    toggle_password_visibility,
)


class AdminWindow(ctk.CTkToplevel):
    # ADMIN WINDOW: initializes the separate administrator sign-in/dashboard window.
    def __init__(self, master, account_store, cars, on_close=None):
        super().__init__(master)
        self.master = master
        self.on_close = on_close
        self.account_store = account_store
        self.car_listing_store = CarListingStore(account_store.database)
        self.cars = cars
        self.transient(master)
        self.title("Auto Deals | Administrator")
        window_width = min(980, master.winfo_screenwidth() - 100)
        window_height = min(740, master.winfo_screenheight() - 120)
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(min(760, window_width), min(600, window_height))
        self.configure(fg_color=COLORS["ivory"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.show_auth_screen("setup" if not self.account_store.has_admin() else "login")
        self.grab_set()
        master.withdraw()

    def close_window(self):
        if self.grab_current() == self:
            self.grab_release()
        self.destroy()
        if self.on_close is not None:
            self.on_close()

    # ADMIN LOGIN WINDOW: builds admin setup or sign-in form.
    def show_auth_screen(self, mode):
        if hasattr(self, "auth_frame"):
            self.auth_frame.destroy()
        self.auth_mode = mode
        self.auth_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["ivory"], corner_radius=0
        )
        self.auth_frame.grid(row=0, column=0, sticky="nsew")
        self.auth_frame.grid_columnconfigure(0, weight=1)
        card = ctk.CTkFrame(
            self.auth_frame, width=450, fg_color=COLORS["card"], corner_radius=16,
            border_width=1, border_color=COLORS["border"]
        )
        card.grid(row=0, column=0, padx=18, pady=18)
        card.grid_columnconfigure(0, weight=1)
        is_setup = mode == "setup"
        ctk.CTkLabel(
            card,
            text="Create the first administrator" if is_setup else "Administrator sign in",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=COLORS["text"]
        ).grid(row=0, column=0, pady=(24, 12))
        if is_setup:
            ctk.CTkLabel(
                card, text="This one-time setup is available only before an admin exists.",
                text_color=COLORS["muted"], wraplength=370
            ).grid(row=2, column=0, padx=30, pady=(0, 8))

        self.auth_entries = {}
        self.password_visibility_buttons = {}
        fields = []
        if is_setup:
            fields.append(("Full name", "full_name", ""))
        fields.extend([
            ("Email address", "email", ""),
            ("Password", "password", "•"),
        ])
        if is_setup:
            fields.append(("Confirm password", "confirm_password", "•"))

        row = 2 if is_setup else 1
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
            card, text="Create Administrator" if is_setup else "Log In",
            height=40, fg_color=COLORS["olive"], hover_color=COLORS["olive_hover"],
            command=self.submit_auth
        ).grid(row=row, column=0, sticky="ew", padx=30, pady=(3, 5))
        if is_setup:
            row += 1
            ctk.CTkLabel(
                card,
                text="Admin setup is local to this app database. Keep the password private.",
                text_color=COLORS["muted"], wraplength=370
            ).grid(row=row, column=0, padx=30, pady=(2, 18))

    # ADMIN LOGIN WINDOW: refreshes the administrator CAPTCHA.
    def refresh_captcha(self):
        challenge, self.captcha_answer = generate_captcha()
        self.captcha_prompt.configure(text=f"Solve: {challenge}")
        self.captcha_entry.delete(0, "end")

    # ADMIN LOGIN WINDOW: reports an authentication validation error.
    def reject_auth(self, message):
        messagebox.showerror("Administrator account", message, parent=self)
        self.refresh_captcha()

    # ADMIN LOGIN WINDOW: validates credentials and enters the dashboard.
    def submit_auth(self):
        if not hmac.compare_digest(
            self.captcha_entry.get().strip().encode("utf-8"),
            self.captcha_answer.encode("utf-8")
        ):
            self.reject_auth("The CAPTCHA answer is incorrect. Please try the new challenge.")
            return

        email = self.auth_entries["email"].get().strip().lower()
        password = self.auth_entries["password"].get()
        if self.auth_mode == "setup":
            if email != ADMIN_OWNER_EMAIL:
                self.reject_auth(
                    f"Only {ADMIN_OWNER_EMAIL} can create the administrator account."
                )
                return
            full_name = self.auth_entries["full_name"].get().strip()
            confirm_password = self.auth_entries["confirm_password"].get()
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
                account = self.account_store.register_initial_admin(
                    full_name, email, password
                )
            except DuplicateAccountError:
                self.reject_auth("An administrator or account with that email already exists.")
                return
            except sqlite3.Error as exc:
                self.reject_auth(f"Could not save the administrator account: {exc}")
                return
        else:
            if not email or not password:
                self.reject_auth("Enter your email address and password.")
                return
            if email != ADMIN_OWNER_EMAIL:
                self.reject_auth("Only the configured owner can sign in as administrator.")
                return
            try:
                account = self.account_store.authenticate(email, password)
            except BannedAccountError:
                self.reject_auth("This administrator account has been banned.")
                return
            except sqlite3.Error as exc:
                self.reject_auth(f"Could not access the account database: {exc}")
                return
            if account is None or account["role"] != "admin":
                self.reject_auth("The administrator email or password is incorrect.")
                return
        self.show_dashboard(account)

    # ADMIN DASHBOARD: renders summary cards and the listings/users tabs.
    def show_dashboard(self, account):
        self.auth_frame.destroy()
        dashboard = ctk.CTkFrame(self, fg_color=COLORS["ivory"], corner_radius=0)
        dashboard.grid(row=0, column=0, sticky="nsew", padx=22, pady=18)
        dashboard.grid_columnconfigure(0, weight=1)
        dashboard.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(dashboard, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        ctk.CTkLabel(
            header, text="Administrator Dashboard",
            font=ctk.CTkFont(size=26, weight="bold"), text_color=COLORS["maroon"]
        ).pack(side="left")
        ctk.CTkButton(
            header, text="Log Out", width=95, fg_color=COLORS["red"],
            hover_color=COLORS["red_hover"], command=self.close_window
        ).pack(side="right")
        ctk.CTkLabel(
            dashboard, text=f'Signed in as {account["full_name"]}',
            text_color=COLORS["muted"]
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        counts = self.account_store.role_counts()
        stats = ctk.CTkFrame(dashboard, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="new", pady=(0, 16))
        for index, (title, value) in enumerate([
            ("Total Accounts", sum(counts.values())),
            ("Buyers", counts["buyer"]),
            ("Sellers", counts["seller"]),
            ("Listings", len(self.cars)),
        ]):
            stats.grid_columnconfigure(index, weight=1)
            card = ctk.CTkFrame(
                stats, fg_color=COLORS["card"], corner_radius=12,
                border_width=1, border_color=COLORS["border"]
            )
            card.grid(row=0, column=index, sticky="ew", padx=5)
            value_label = ctk.CTkLabel(
                card, text=str(value), font=ctk.CTkFont(size=23, weight="bold"),
                text_color=COLORS["olive"]
            )
            value_label.pack(anchor="w", padx=14, pady=(12, 2))
            if title == "Listings":
                self.listing_count_label = value_label
            ctk.CTkLabel(
                card, text=title, text_color=COLORS["muted"]
            ).pack(anchor="w", padx=14, pady=(0, 12))

        self.admin_tabs = ctk.CTkTabview(
            dashboard, fg_color=COLORS["card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"]
        )
        self.admin_tabs.grid(row=3, column=0, sticky="nsew")
        listings = self.admin_tabs.add("Listings")
        listings.grid_columnconfigure(0, weight=1)
        listings.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            listings, text="Marketplace Listings",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["maroon"]
        ).grid(row=0, column=0, sticky="w", padx=16, pady=14)
        listing_rows = ctk.CTkScrollableFrame(listings, fg_color="transparent")
        listing_rows.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.listing_rows = listing_rows
        users = self.admin_tabs.add("Users")
        users.grid_columnconfigure(0, weight=1)
        users.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            users, text="User Accounts",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["maroon"]
        ).grid(row=0, column=0, sticky="w", padx=16, pady=14)
        self.user_rows = ctk.CTkScrollableFrame(users, fg_color="transparent")
        self.user_rows.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.render_listings()
        self.render_users()

    # ADMIN DASHBOARD / USERS TAB: renders accounts and ban controls.
    def render_users(self):
        for widget in self.user_rows.winfo_children():
            widget.destroy()
        accounts = self.account_store.list_accounts()
        if not accounts:
            ctk.CTkLabel(
                self.user_rows, text="There are no accounts.",
                text_color=COLORS["muted"]
            ).pack(padx=12, pady=16)
            return
        for account in accounts:
            row = ctk.CTkFrame(
                self.user_rows, fg_color=COLORS["ivory"], corner_radius=8
            )
            row.pack(fill="x", padx=4, pady=4)
            details = ctk.CTkFrame(row, fg_color="transparent")
            details.pack(side="left", fill="x", expand=True, padx=12, pady=9)
            ctk.CTkLabel(
                details, text=account["full_name"], anchor="w",
                font=ctk.CTkFont(weight="bold"), text_color=COLORS["text"]
            ).pack(anchor="w")
            status = "Banned" if account["is_banned"] else "Active"
            ctk.CTkLabel(
                details,
                text=f'{account["email"]}  ·  {account["role"].title()}  ·  {status}',
                anchor="w", text_color=COLORS["muted"]
            ).pack(anchor="w")
            if account["role"] == "admin":
                continue
            banned = bool(account["is_banned"])
            ctk.CTkButton(
                row, text="Unban" if banned else "Ban", width=82,
                fg_color=COLORS["olive"] if banned else COLORS["red"],
                hover_color=COLORS["olive_hover"] if banned else COLORS["red_hover"],
                command=lambda email=account["email"], ban=not banned:
                    self.change_user_ban(email, ban),
            ).pack(side="right", padx=12, pady=10)

    # ADMIN DASHBOARD / USERS TAB: bans or unbans an account.
    def change_user_ban(self, email, banned):
        action = "ban this user and remove their listings" if banned else "unban this user"
        if not messagebox.askyesno(
            "Confirm account change",
            f"Are you sure you want to {action}?",
            parent=self,
        ):
            return
        try:
            removed_listing_ids = self.account_store.set_banned(email, banned)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror(
                "User management", f"The account could not be updated: {exc}",
                parent=self,
            )
            return
        if banned and removed_listing_ids:
            removed_ids = set(removed_listing_ids)
            self.cars[:] = [
                car for car in self.cars if car.get("id") not in removed_ids
            ]
            self.render_listings()
            self.listing_count_label.configure(text=str(len(self.cars)))
        self.render_users()
        if banned:
            message = (
                f"The account was banned and {len(removed_listing_ids)} listing(s) removed."
            )
        else:
            message = "The account was unbanned."
        messagebox.showinfo("User management", message, parent=self)

    # ADMIN DASHBOARD / LISTINGS TAB: renders marketplace posts.
    def render_listings(self):
        for widget in self.listing_rows.winfo_children():
            widget.destroy()
        if not self.cars:
            ctk.CTkLabel(
                self.listing_rows, text="There are no current listings.",
                text_color=COLORS["muted"]
            ).pack(padx=12, pady=16)
            return
        for car in self.cars:
            row = ctk.CTkFrame(
                self.listing_rows, fg_color=COLORS["ivory"], corner_radius=8
            )
            row.pack(fill="x", padx=4, pady=4)
            details = ctk.CTkFrame(row, fg_color="transparent")
            details.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            ctk.CTkLabel(
                details, text=f'{car["model"]} ({car["year"]})',
                text_color=COLORS["text"], anchor="w"
            ).pack(anchor="w")
            ctk.CTkLabel(
                details, text=f'Seller: {car.get("seller_email") or "Unknown (older listing)"}',
                text_color=COLORS["muted"], anchor="w"
            ).pack(anchor="w")
            ctk.CTkLabel(
                row, text=f'₱ {int(float(car["price"])):,.0f}',
                text_color=COLORS["olive"], font=ctk.CTkFont(weight="bold")
            ).pack(side="right", padx=10)
            ctk.CTkButton(
                row, text="Remove", width=76, fg_color=COLORS["red"],
                hover_color=COLORS["red_hover"],
                command=lambda listing=car: self.remove_listing(listing),
            ).pack(side="right", padx=8, pady=8)

    # ADMIN DASHBOARD / LISTINGS TAB: removes a post from the marketplace.
    def remove_listing(self, car):
        if not messagebox.askyesno(
            "Remove listing",
            f'Remove "{car["model"]} ({car["year"]})" from the marketplace?',
            parent=self,
        ):
            return
        try:
            deleted = self.car_listing_store.delete(car["id"])
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Remove listing", f"The listing could not be removed: {exc}",
                parent=self,
            )
            return
        if deleted:
            self.cars[:] = [
                listing for listing in self.cars if listing.get("id") != car["id"]
            ]
            self.render_listings()
            self.listing_count_label.configure(text=str(len(self.cars)))
