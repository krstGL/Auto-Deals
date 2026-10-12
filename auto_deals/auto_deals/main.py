import customtkinter as ctk
from tkinter import Canvas, filedialog, messagebox
import os
import re
import sqlite3
from PIL import Image, ImageDraw, ImageOps, ImageTk

from .admin import AdminWindow
from .auth import AuthenticationPages
from .buyer import BuyerPages
from .common import (
    ADMIN_OWNER_EMAIL,
    AccountStore,
    CarListingStore,
    COLORS,
    MessagingStore,
)
from .database import Database
from .seller import SellerPages


class AutoDealsApp(AuthenticationPages, BuyerPages, SellerPages, ctk.CTk):
    # MAIN APP WINDOW: initializes shared UI state, stores, and startup page.
    def __init__(self):
        super().__init__()
        self.title("Auto Deals | Second-hand Car Marketplace")
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.set_auth_geometry()
        self.configure(fg_color=COLORS["ivory"])
        self.favorites = set()
        self.photo_path = ""
        self.profile_photo_path = ""
        self.profile_photos = {}
        self.profile_photo_image = None
        self.current_user = None
        self.database = Database()
        self.database.initialize()
        self.car_photo_directory = os.path.join(
            self.database.path.parent, "car_photos"
        )
        self.account_store = AccountStore(self.database)
        self.car_listing_store = CarListingStore(self.database)
        self.messaging_store = MessagingStore(self.database)
        self.cars = self.car_listing_store.list_all()
        self.current_page = "Dashboard"
        self.sidebar_buttons = {}
        self.auth_frame = None
        self.admin_window = None
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_sidebar()
        self.build_main_area()
        self.show_auth_screen("login")
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

    # MAIN APP WINDOW: opens the separate administrator window.
    def open_admin_window(self):
        if self.admin_window is not None and self.admin_window.winfo_exists():
            self.admin_window.lift()
            self.admin_window.focus_force()
            return
        self.admin_window = AdminWindow(
            self, self.account_store, self.cars,
            on_close=self.restore_login_after_admin,
        )

    # LOGIN WINDOW: restores the main sign-in window after admin closes.
    def restore_login_after_admin(self):
        self.admin_window = None
        if self.winfo_exists():
            self.deiconify()
            self.lift()
            self.focus_force()

    # LOGIN WINDOW: sizes and centers the sign-in window.
    def set_auth_geometry(self):
        auth_width = min(820, self.screen_width - 80)
        auth_height = min(700, self.screen_height - 100)
        self.minsize(min(480, auth_width), min(480, auth_height))
        self.geometry(
            f"{auth_width}x{auth_height}+"
            f"{(self.screen_width - auth_width) // 2}+"
            f"{(self.screen_height - auth_height) // 2}"
        )

    # MAIN APP WINDOW: creates the navigation sidebar.
    def build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=225, corner_radius=0, fg_color=COLORS["maroon"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(
            self.sidebar,
            text="AUTO DEALS",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["ivory"],
        ).pack(anchor="w", padx=20, pady=(24, 22))
        nav_groups = [
            ("MAIN MENU", [("⌂", "Dashboard"), ("▦", "Browse Cars"), ("♡", "Favorites"), ("⇄", "Compare Cars"), ("✉", "Messages")]),
            ("SELLER TOOLS", [("＋", "Add New Car"), ("▤", "My Listings"), ("▣", "Inquiries")]),
            ("ACCOUNT", [("♙", "My Profile"), ("⚙", "Settings")]),
        ]
        self.seller_tools_section = None
        self.account_section_heading = None
        for heading, items in nav_groups:
            if heading == "SELLER TOOLS":
                self.seller_tools_section = ctk.CTkFrame(
                    self.sidebar, fg_color="transparent"
                )
                section = self.seller_tools_section
                section.pack(fill="x")
            else:
                section = self.sidebar
                if heading == "ACCOUNT":
                    self.account_section_heading = ctk.CTkLabel(
                        section, text=heading,
                        font=ctk.CTkFont(size=10, weight="bold"),
                        text_color="#D3B7A9"
                    )
                    self.account_section_heading.pack(
                        anchor="w", padx=20, pady=(6, 7)
                    )
                    heading = None
            if heading:
                ctk.CTkLabel(
                    section, text=heading,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="#D3B7A9"
                ).pack(anchor="w", padx=20, pady=(6, 7))
            for icon, label in items:
                btn = ctk.CTkButton(
                    section, text=f"{icon}   {label}", anchor="w", height=38,
                    corner_radius=8, fg_color="transparent", hover_color=COLORS["maroon_hover"],
                    text_color=COLORS["ivory"], font=ctk.CTkFont(size=13),
                    command=lambda p=label: self.show_page(p)
                )
                btn.pack(fill="x", padx=12, pady=2)
                self.sidebar_buttons[label] = btn
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True, fill="both")
        ctk.CTkButton(self.sidebar, text="↪   Logout", height=40, corner_radius=8,
                      fg_color=COLORS["red"], hover_color=COLORS["red_hover"],
                      text_color="white", font=ctk.CTkFont(size=13, weight="bold"),
                      command=self.logout).pack(fill="x", padx=12, pady=(10, 20))

    # MAIN APP WINDOW: creates the top bar and page content area.
    def build_main_area(self):
        self.main = ctk.CTkFrame(self, fg_color=COLORS["ivory"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self.main, height=68, corner_radius=0, fg_color=COLORS["card"],
                           border_width=1, border_color=COLORS["border"])
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        self.account_button = ctk.CTkButton(
            top, text="Account  ▾", width=150, height=36, fg_color=COLORS["maroon"],
            hover_color=COLORS["maroon_hover"], command=lambda: self.show_page("My Profile")
        )
        self.account_button.grid(row=0, column=1, padx=(4, 20))
        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=24, pady=22)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    # MAIN APP WINDOW: clears the active page before navigation.
    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # MAIN APP WINDOW: selects and displays a buyer or seller page.
    def show_page(self, page):
        if (
            page in ("Add New Car", "My Listings", "Inquiries")
            and (not self.current_user or self.current_user.get("role") != "seller")
        ):
            page = "Dashboard"
        self.current_page = page
        for name, btn in self.sidebar_buttons.items():
            btn.configure(fg_color=COLORS["olive"] if name == page else "transparent")
        self.clear_content()
        pages = {
            "Dashboard": self.page_dashboard,
            "Browse Cars": self.page_browse,
            "Favorites": self.page_favorites,
            "Compare Cars": self.page_compare,
            "Messages": self.page_messages,
            "Add New Car": self.page_add_car,
            "My Listings": self.page_listings,
            "Inquiries": self.page_inquiries,
            "My Profile": self.page_profile,
            "Settings": self.page_settings,
        }
        pages.get(page, self.page_dashboard)()

    # MAIN APP WINDOW: shows or hides seller-only navigation controls.
    def set_seller_tools_visible(self, visible):
        if not self.seller_tools_section:
            return
        if visible:
            if not self.seller_tools_section.winfo_manager():
                self.seller_tools_section.pack(
                    fill="x", before=self.account_section_heading
                )
        else:
            self.seller_tools_section.pack_forget()

    # MAIN APP WINDOW: shared page heading used by buyer and seller pages.
    def page_heading(self, title, subtitle):
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=27, weight="bold"),
                     text_color=COLORS["maroon"]).pack(anchor="w")
        ctk.CTkLabel(header, text=subtitle, font=ctk.CTkFont(size=13),
                     text_color=COLORS["muted"]).pack(anchor="w", pady=(4, 0))

    # MAIN APP WINDOW: shared dashboard statistic card.
    def stat_card(self, parent, title, value, icon):
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12,
                            border_width=1, border_color=COLORS["border"])
        card.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=23), text_color=COLORS["olive"]).pack(anchor="w", padx=15, pady=(13, 4))
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=23, weight="bold"), text_color=COLORS["text"]).pack(anchor="w", padx=15)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color=COLORS["muted"]).pack(anchor="w", padx=15, pady=(1, 14))

    # MAIN APP WINDOW: shared informational card.
    def info_card(self, title, description):
        card = ctk.CTkFrame(self.content, fg_color=COLORS["card"], corner_radius=12,
                            border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=8, padx=3)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=17, weight="bold"), text_color=COLORS["maroon"]).pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(card, text=description, text_color=COLORS["muted"], wraplength=700).pack(anchor="w", padx=18, pady=(0, 18))

    # ACCOUNT WINDOW / PROFILE PAGE: builds the editable profile form.
    def page_profile(self):
        self.page_heading("My Profile", "Manage your account information.")
        card = ctk.CTkFrame(self.content, fg_color=COLORS["card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", padx=2)
        avatar_area = ctk.CTkFrame(card, fg_color="transparent")
        avatar_area.pack(pady=(20, 0))
        self.profile_avatar = Canvas(
            avatar_area, width=128, height=128, highlightthickness=0,
            background=COLORS["card"]
        )
        self.profile_avatar.pack()
        self.render_profile_avatar()
        ctk.CTkButton(
            avatar_area, text="Change Profile Picture", height=32,
            fg_color=COLORS["maroon"], hover_color=COLORS["maroon_hover"],
            command=self.choose_profile_picture
        ).pack(pady=(10, 0))
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=20)
        form.grid_columnconfigure((0, 1), weight=1)
        self.profile_entries = {}
        profile_fields = [
            ("Full Name", "full_name", "Enter your full name"),
            ("Email Address", "email", "Enter your email address"),
            ("Phone Number", "phone_number", "Enter your phone number"),
            ("Location", "location", "Enter your location"),
        ]
        for i, (label, key, placeholder) in enumerate(profile_fields):
            r, c = divmod(i, 2)
            ctk.CTkLabel(form, text=label, text_color=COLORS["text"]).grid(row=r*2, column=c, sticky="w", padx=8, pady=(5, 4))
            entry = ctk.CTkEntry(
                form, placeholder_text=placeholder, height=38,
                fg_color=COLORS["ivory"], border_color=COLORS["border"]
            )
            entry.grid(row=r*2+1, column=c, sticky="ew", padx=8, pady=(0, 12))
            if self.current_user:
                entry.insert(0, self.current_user.get(key, ""))
            self.profile_entries[key] = entry
        ctk.CTkButton(card, text="Save Profile", fg_color=COLORS["olive"], hover_color=COLORS["olive_hover"],
                      command=self.save_profile).pack(anchor="e", padx=28, pady=(0, 20))

    # ACCOUNT WINDOW / PROFILE PAGE: validates and saves profile changes.
    def save_profile(self):
        if not self.current_user:
            messagebox.showerror(
                "Profile", "Log in before saving profile information.", parent=self
            )
            return
        full_name = self.profile_entries["full_name"].get().strip()
        if not full_name:
            messagebox.showerror(
                "Profile", "Full name is required.", parent=self
            )
            return
        email = self.profile_entries["email"].get().strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            messagebox.showerror(
                "Profile", "Enter a valid email address.", parent=self
            )
            return
        phone_number = self.profile_entries["phone_number"].get().strip()
        location = self.profile_entries["location"].get().strip()
        old_email = self.current_user["email"]
        if (
            self.current_user.get("role") == "admin"
            and email != ADMIN_OWNER_EMAIL
        ):
            messagebox.showerror(
                "Profile",
                "The administrator owner's email address cannot be changed.",
                parent=self,
            )
            return
        profile_photo = self.profile_photos.get(
            old_email,
            self.profile_photo_path or self.current_user.get("profile_photo", "")
        )
        try:
            self.account_store.update_profile(
                old_email, email, full_name, phone_number, location, profile_photo
            )
        except sqlite3.IntegrityError as exc:
            detail = str(exc).lower()
            if "accounts.email" in detail:
                error = "An account with that email address already exists."
            else:
                error = f"Could not save profile changes: {exc}"
            messagebox.showerror("Profile", error, parent=self)
            return
        except ValueError as exc:
            messagebox.showerror("Profile", str(exc), parent=self)
            return
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Profile", f"Could not save profile changes: {exc}", parent=self
            )
            return
        if old_email != email:
            self.profile_photos[email] = self.profile_photos.pop(
                old_email, profile_photo
            )
            for car in self.cars:
                if car.get("seller_email") == old_email:
                    car["seller_email"] = email
        self.current_user.update({
            "email": email,
            "full_name": full_name,
            "phone_number": phone_number,
            "location": location,
            "profile_photo": profile_photo,
        })
        self.profile_photo_path = profile_photo
        self.account_button.configure(text=f'{full_name.split()[0]}  ▾')
        self.show_page("My Profile")
        messagebox.showinfo(
            "Profile", "Your profile was saved successfully.", parent=self
        )

    # ACCOUNT WINDOW / PROFILE PAGE: chooses a profile photo.
    def choose_profile_picture(self):
        path = filedialog.askopenfilename(
            title="Choose profile picture",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp")]
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, ValueError):
            messagebox.showerror(
                "Invalid image", "Choose a valid image file for your profile picture.",
                parent=self
            )
            return
        self.profile_photo_path = path
        if self.current_user:
            self.profile_photos[self.current_user["email"]] = path
        self.render_profile_avatar()

    # ACCOUNT WINDOW / PROFILE PAGE: draws the current user's avatar.
    def render_profile_avatar(self):
        self.profile_avatar.delete("all")
        if self.current_user:
            self.profile_photo_path = self.profile_photos.get(
                self.current_user["email"],
                self.current_user.get("profile_photo", "")
            )
        if self.profile_photo_path:
            with Image.open(self.profile_photo_path) as source:
                avatar = ImageOps.fit(source.convert("RGBA"), (120, 120))
            mask = Image.new("L", (120, 120), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 119, 119), fill=255)
            avatar.putalpha(mask)
            self.profile_photo_image = ImageTk.PhotoImage(avatar, master=self)
            self.profile_avatar.create_image(
                64, 64, image=self.profile_photo_image
            )
            return

        self.profile_avatar.create_oval(
            4, 4, 124, 124, fill=COLORS["khaki"], outline=""
        )
        initials = "?"
        if self.current_user:
            name_parts = self.current_user.get("full_name", "").split()
            if name_parts:
                initials = "".join(part[0] for part in name_parts[:2]).upper()
        self.profile_avatar.create_text(
            64, 64, text=initials, font=("Segoe UI", 34, "bold"),
            fill=COLORS["maroon"]
        )

    # ACCOUNT WINDOW / SETTINGS PAGE: displays application preferences.
    def page_settings(self):
        self.page_heading("Settings", "Application preferences and account options.")
        self.info_card("Appearance", "Auto Deals uses the maroon, khaki, olive green, and ivory color palette.")
        ctk.CTkButton(self.content, text="Toggle Light / Dark Appearance", fg_color=COLORS["olive"],
                      hover_color=COLORS["olive_hover"], command=self.toggle_theme).pack(anchor="w", pady=10)
        ctk.CTkButton(
            self.content, text="Log Out", fg_color=COLORS["red"],
            hover_color=COLORS["red_hover"], command=self.logout
        ).pack(anchor="w", pady=(4, 10))

    # ACCOUNT WINDOW / SETTINGS PAGE: toggles the application appearance.
    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("dark" if current == "Light" else "light")
        messagebox.showinfo("Appearance", "Appearance changed. Some custom-colored panels remain on the Auto Deals theme.")

    # MAIN APP WINDOW: returns the user to the login window.
    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to log out of Auto Deals?"):
            self.current_page = "Authentication"
            self.current_user = None
            self.set_seller_tools_visible(False)
            self.show_auth_screen("login")

if __name__ == "__main__":
    app = AutoDealsApp()
    app.mainloop()
