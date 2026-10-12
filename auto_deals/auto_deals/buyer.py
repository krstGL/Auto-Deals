import customtkinter as ctk
from tkinter import messagebox
import sqlite3
from PIL import Image, ImageOps
import os

from .common import COLORS


def car_grid_column_count(width):
    if width >= 760:
        return 3
    if width >= 500:
        return 2
    return 1


def fit_listing_photo(source_image, size):
    return ImageOps.pad(
        source_image, size, method=Image.Resampling.LANCZOS,
        color="#E9DDBF",
    )


def listings_for_seller(cars, email):
    normalized_email = email.strip().lower()
    return [
        car for car in cars
        if car.get("seller_email", "").strip().lower() == normalized_email
    ]


def can_contact_seller(user, car):
    return bool(user and user.get("role") == "buyer")


class BuyerPages:
    # BUYER / SELLER DASHBOARD WINDOW: shows role-specific dashboard content.
    def page_dashboard(self):
        is_seller = self.current_user and self.current_user.get("role") == "seller"
        self.page_heading(
            "Seller Dashboard" if is_seller else "Buyer Dashboard",
            "Manage your vehicle listings." if is_seller
            else "Find your next car with confidence."
        )
        if is_seller:
            ctk.CTkButton(
                self.content, text="+ Add New Car", fg_color=COLORS["olive"],
                hover_color=COLORS["olive_hover"],
                command=lambda: self.show_page("Add New Car")
            ).pack(anchor="e", pady=(0, 12))
        if is_seller:
            seller_cars = listings_for_seller(
                self.cars, self.current_user["email"]
            )
            stats = ctk.CTkFrame(self.content, fg_color="transparent")
            stats.pack(fill="x", pady=(0, 18))
            self.stat_card(stats, "Your Listings", str(len(seller_cars)), "🚘")
            self.stat_card(stats, "Marketplace Listings", str(len(self.cars)), "▤")
            self.stat_card(stats, "Favorite Cars", str(len(self.favorites)), "♡")
            featured_label = "SELLER OVERVIEW"
            featured_title = "Your listed vehicles"
            featured_description = (
                "Manage and review the vehicles you have posted."
            )
            featured_action = "Manage listings"
            featured_command = lambda: self.show_page("My Listings")
        else:
            stats = ctk.CTkFrame(self.content, fg_color="transparent")
            stats.pack(fill="x", pady=(0, 18))
            self.stat_card(stats, "Saved Cars", str(len(self.cars)), "🚘")
            self.stat_card(stats, "Favorite Cars", str(len(self.favorites)), "♡")
            self.stat_card(stats, "Recently Viewed", "5", "◷")
            self.stat_card(stats, "Active Searches", "3", "⌕")

            hero = ctk.CTkFrame(
                self.content, fg_color=COLORS["maroon"], corner_radius=14
            )
            hero.pack(fill="x", pady=(0, 18))
            left = ctk.CTkFrame(hero, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=24, pady=24)
            ctk.CTkLabel(
                left, text="FIND THE RIGHT CAR\nAT THE RIGHT PRICE",
                justify="left", font=ctk.CTkFont(size=23, weight="bold"),
                text_color=COLORS["ivory"],
            ).pack(anchor="w")
            ctk.CTkLabel(
                left, text="Explore second-hand vehicles from sellers near you.",
                font=ctk.CTkFont(size=13), text_color="#E8DCCB",
            ).pack(anchor="w", pady=(8, 15))
            ctk.CTkButton(
                left, text="Browse Cars  →", fg_color=COLORS["olive"],
                hover_color=COLORS["olive_hover"],
                command=lambda: self.show_page("Browse Cars"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                hero, text="AUTO\nDEALS",
                font=ctk.CTkFont(size=32, weight="bold"),
                text_color=COLORS["khaki"],
            ).pack(side="right", padx=45, pady=25)
            seller_cars = self.cars
            featured_label = "CURATED FOR YOU"
            featured_title = "Pick your favorites"
            featured_description = (
                "Explore standout vehicles and find the one that feels right."
            )
            featured_action = "View all"
            featured_command = lambda: self.show_page("Browse Cars")

        self.featured_heading = ctk.CTkFrame(
            self.content, fg_color="transparent"
        )
        self.featured_heading.pack(fill="x", pady=(5, 3))
        ctk.CTkLabel(
            self.featured_heading, text=featured_label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["muted"],
        ).pack(anchor="w")
        featured_title_row = ctk.CTkFrame(
            self.featured_heading, fg_color="transparent"
        )
        featured_title_row.pack(fill="x")
        ctk.CTkLabel(
            featured_title_row, text=featured_title,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")
        ctk.CTkButton(
            featured_title_row, text=featured_action, width=110, height=28,
            corner_radius=14, fg_color="transparent",
            hover_color=COLORS["khaki"], text_color=COLORS["olive"],
            command=featured_command,
        ).pack(side="right")
        ctk.CTkLabel(
            self.featured_heading,
            text=featured_description,
            font=ctk.CTkFont(size=12), text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(2, 3))
        self.car_grid(self.content, seller_cars[:3], featured=True)

    # BUYER / SELLER WINDOW: reusable section heading and action button.
    def section_title(self, parent, title, action, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(4, 10))
        ctk.CTkLabel(row, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkButton(row, text=action, width=80, height=28, fg_color="transparent",
                      hover_color=COLORS["khaki"], text_color=COLORS["olive"], command=command).pack(side="right")

    # BUYER / SELLER WINDOW: renders listing cards for dashboard and browsing pages.
    def car_grid(self, parent, cars, featured=False):
        wrap = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        if not cars:
            ctk.CTkLabel(wrap, text="No cars found. Try another search or add a listing.",
                         text_color=COLORS["muted"]).pack(pady=35)
            return
        cards = []
        for car in cars:
            card = ctk.CTkFrame(
                wrap, fg_color=COLORS["card"], corner_radius=12,
                border_width=1, border_color=COLORS["border"],
            )
            cards.append(card)
            card.grid(sticky="nsew", padx=7, pady=7)
            photo = car.get("photo", "")
            image_label = None
            source_image = None
            if photo and os.path.exists(photo):
                try:
                    with Image.open(photo) as source:
                        source_image = source.convert("RGB").copy()
                except (OSError, ValueError):
                    source_image = None

            image_frame = ctk.CTkFrame(
                card, height=132 if featured else 124,
                fg_color="#E9DDBF", corner_radius=10,
            )
            card._car_image_frame = image_frame
            image_frame.pack(fill="x", padx=8, pady=(8, 0))
            image_frame.pack_propagate(False)
            if source_image is not None:
                image_label = ctk.CTkLabel(
                    image_frame, text="", corner_radius=10
                )
                image_label.pack(fill="both", expand=True, padx=4, pady=4)
                card._car_source_image = source_image
                card._car_image_label = image_label
                card._car_image_size = None
            else:
                ctk.CTkLabel(
                    image_frame, text="🚘",
                    font=ctk.CTkFont(size=42),
                    text_color=COLORS["maroon"],
                ).pack(expand=True)

            badges = ctk.CTkFrame(card, fg_color="transparent")
            badges.pack(fill="x", padx=11, pady=(7, 0))
            ctk.CTkLabel(
                badges, text=car.get("body") or "Vehicle",
                fg_color="#EFE5D3", text_color=COLORS["text"],
                corner_radius=9, padx=9, pady=3,
                font=ctk.CTkFont(size=10, weight="bold"),
            ).pack(side="left")
            if car.get("condition"):
                ctk.CTkLabel(
                    badges, text=car["condition"],
                    fg_color="#E7EBD9", text_color=COLORS["olive"],
                    corner_radius=9, padx=9, pady=3,
                    font=ctk.CTkFont(size=10, weight="bold"),
                ).pack(side="left", padx=(6, 0))

            details = ctk.CTkFrame(card, fg_color="transparent")
            details.pack(fill="x", padx=11, pady=(6, 0))
            details.grid_columnconfigure(0, weight=1)
            title = f'{car["model"]} {car["year"]}'
            ctk.CTkLabel(
                details, text=title, anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["text"],
            ).grid(row=0, column=0, sticky="ew")
            ctk.CTkLabel(
                details, text=f'₱ {int(float(car["price"])):,.0f}',
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["text"],
            ).grid(row=0, column=1, sticky="e", padx=(8, 0))
            description = car.get("description", "").strip()
            if len(description) > 105:
                description = description[:102].rsplit(" ", 1)[0] + "..."
            if not description:
                description = (
                    f'{car["mileage"]} km · {car["transmission"]} · '
                    f'{car["location"]}'
                )
            ctk.CTkLabel(
                card, text=description, anchor="w", justify="left",
                wraplength=300, height=36,
                font=ctk.CTkFont(size=10), text_color=COLORS["muted"],
            ).pack(fill="x", padx=11, pady=(4, 0))
            ctk.CTkLabel(
                card,
                text=f'{car["mileage"]} km  ·  {car["transmission"]}  ·  {car["location"]}',
                anchor="w", font=ctk.CTkFont(size=10),
                text_color=COLORS["muted"],
            ).pack(fill="x", padx=11, pady=(3, 0))
            buttons = ctk.CTkFrame(card, fg_color="transparent")
            buttons.pack(fill="x", padx=9, pady=(7, 9))
            ctk.CTkButton(
                buttons, text="View Details", height=29, corner_radius=14,
                fg_color=COLORS["maroon"], hover_color=COLORS["maroon_hover"],
                command=lambda c=car: self.show_car_details(c),
            ).pack(side="left", expand=True, fill="x", padx=(0, 4))
            if can_contact_seller(self.current_user, car):
                ctk.CTkButton(
                    buttons, text="Contact Seller", height=29,
                    corner_radius=14, fg_color=COLORS["olive"],
                    hover_color=COLORS["olive_hover"],
                    command=lambda c=car: self.start_seller_conversation(c),
                ).pack(side="left", expand=True, fill="x", padx=(0, 4))
            ctk.CTkButton(
                buttons, text="♡", width=32, height=29, corner_radius=14,
                fg_color="#EFE5D3", hover_color=COLORS["khaki"],
                text_color=COLORS["text"],
                command=lambda c=car: self.toggle_favorite(c),
            ).pack(side="right")

        def layout_cards(width):
            columns = car_grid_column_count(width)
            for index in range(3):
                wrap.grid_columnconfigure(
                    index, weight=1 if index < columns else 0,
                    uniform="car_cards" if index < columns else "",
                )
            row_count = (len(cards) + columns - 1) // columns
            for row in range(row_count):
                wrap.grid_rowconfigure(row, weight=1, uniform="car_rows")
            for index, card in enumerate(cards):
                card.grid_configure(
                    row=index // columns, column=index % columns,
                    sticky="nsew", padx=7, pady=7,
                )
                card_width = max(
                    180, (width - columns * 14) // columns
                )
                image_width = min(150, max(110, card_width - 24))
                card._car_image_frame.configure(height=image_width + 8)
                image_label = getattr(card, "_car_image_label", None)
                source_image = getattr(card, "_car_source_image", None)
                if image_label is not None and source_image is not None:
                    image_size = (image_width, image_width)
                    if getattr(card, "_car_image_size", None) != image_size:
                        image = fit_listing_photo(source_image, image_size)
                        card._car_ctk_image = ctk.CTkImage(
                            light_image=image, dark_image=image,
                            size=image_size,
                        )
                        image_label.configure(image=card._car_ctk_image)
                        card._car_image_size = image_size

        wrap.bind(
            "<Configure>",
            lambda event: layout_cards(event.width),
        )
        wrap.after_idle(lambda: layout_cards(wrap.winfo_width()))

    # BUYER / SELLER WINDOW: displays the fallback when a listing has no photo.
    def photo_placeholder(self, parent, featured=False):
        height = 160 if featured else 115
        ph = ctk.CTkFrame(parent, height=height, fg_color="#E9E0D1", corner_radius=8)
        ph.pack(
            fill="x", padx=8 if featured else 10,
            pady=(8, 0) if featured else (10, 5)
        )
        ph.pack_propagate(False)
        ctk.CTkLabel(ph, text="🚘", font=ctk.CTkFont(size=42), text_color=COLORS["maroon"]).pack(expand=True)

    # BUYER WINDOW: builds the searchable and sortable vehicle listing page.
    def page_browse(self):
        self.page_heading("Browse Vehicles", "Search and filter available second-hand cars.")
        filters = ctk.CTkFrame(self.content, fg_color=COLORS["card"], corner_radius=12,
                               border_width=1, border_color=COLORS["border"])
        filters.pack(fill="x", pady=(0, 14))
        self.browse_search = ctk.CTkEntry(filters, placeholder_text="Model or location...", width=260)
        self.browse_search.pack(side="left", padx=12, pady=12)
        self.browse_sort = ctk.CTkOptionMenu(filters, values=["Newest First", "Price: Low to High", "Price: High to Low"],
                                             fg_color=COLORS["olive"], button_color=COLORS["olive_hover"])
        self.browse_sort.pack(side="left", padx=8, pady=12)
        ctk.CTkButton(filters, text="Search", fg_color=COLORS["olive"], hover_color=COLORS["olive_hover"],
                      command=self.run_browse_search).pack(side="left", padx=8)
        ctk.CTkButton(filters, text="Reset", fg_color=COLORS["khaki"], hover_color=COLORS["olive"],
                      text_color=COLORS["text"], command=lambda: self.show_page("Browse Cars")).pack(side="left", padx=8)
        self.browse_results = ctk.CTkFrame(self.content, fg_color="transparent")
        self.browse_results.pack(fill="both", expand=True)
        self.car_grid(self.browse_results, self.cars)

    # BUYER WINDOW: filters and sorts the currently available vehicles.
    def run_browse_search(self):
        query = self.browse_search.get().strip().lower()
        cars = [
            car for car in self.cars
            if query in " ".join(str(value) for value in car.values()).lower()
        ]
        sort = self.browse_sort.get()
        if sort == "Price: Low to High":
            cars.sort(key=lambda car: float(car["price"]))
        elif sort == "Price: High to Low":
            cars.sort(key=lambda car: float(car["price"]), reverse=True)
        for w in self.browse_results.winfo_children():
            w.destroy()
        self.car_grid(self.browse_results, cars)

    # BUYER WINDOW: displays the signed-in buyer's saved vehicles.
    def page_favorites(self):
        self.page_heading("My Favorites", "Vehicles you have saved.")
        self.car_grid(self.content, [c for c in self.cars if c.get("id", id(c)) in self.favorites])

    # BUYER WINDOW: adds/removes a vehicle from the favorites collection.
    def toggle_favorite(self, car):
        key = car.get("id", id(car))
        if key in self.favorites:
            self.favorites.remove(key)
        else:
            self.favorites.add(key)
        messagebox.showinfo("Favorites", "Favorites updated.")
        if self.current_page in ("Dashboard", "Favorites"):
            self.show_page(self.current_page)

    # BUYER WINDOW: opens product details and seller contact action.
    def show_car_details(self, car):
        win = ctk.CTkToplevel(self)
        win.title(f'{car["model"]} Details')
        win.geometry("650x600")
        win.configure(fg_color=COLORS["ivory"])
        ctk.CTkLabel(win, text=f'{car["model"]} {car["year"]}',
                     font=ctk.CTkFont(size=25, weight="bold"), text_color=COLORS["maroon"]).pack(anchor="w", padx=25, pady=(25, 8))
        photo = car.get("photo", "")
        if photo and os.path.exists(photo):
            try:
                img = ctk.CTkImage(light_image=Image.open(photo), size=(560, 220))
                pic = ctk.CTkLabel(win, text="", image=img)
                pic.image = img
                pic.pack(padx=25, pady=10)
            except Exception:
                pass
        ctk.CTkLabel(win, text=f'₱ {int(float(car["price"])):,.0f}', font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=COLORS["olive"]).pack(anchor="w", padx=25, pady=4)
        details = f'Mileage: {car["mileage"]} km\\nTransmission: {car["transmission"]}\\nFuel: {car["fuel"]}\\nBody type: {car["body"]}\\nCondition: {car["condition"]}\\nLocation: {car["location"]}\\n\\n{car["description"]}'
        ctk.CTkLabel(win, text=details, justify="left", text_color=COLORS["text"],
                     font=ctk.CTkFont(size=14)).pack(anchor="w", padx=25, pady=10)

        if (
            can_contact_seller(self.current_user, car)
        ):
            ctk.CTkButton(
                win, text="Contact Seller", height=38,
                fg_color=COLORS["maroon"], hover_color=COLORS["maroon_hover"],
                command=lambda: self.start_seller_conversation(car, win),
            ).pack(anchor="w", padx=25, pady=(8, 20))

    # BUYER WINDOW: opens or creates a conversation with a listing's seller.
    def start_seller_conversation(self, car, details_window=None):
        try:
            conversation_id = self.messaging_store.start_conversation(
                car["id"], self.current_user["email"]
            )
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror(
                "Messages", f"Could not start a conversation: {exc}", parent=self
            )
            return
        if details_window is not None:
            details_window.destroy()
        conversation = next(
            (
                item for item in self.messaging_store.list_conversations(
                    self.current_user["email"]
                )
                if item["id"] == conversation_id
            ),
            None,
        )
        if conversation is None:
            messagebox.showerror(
                "Messages",
                "The conversation was created but could not be loaded.",
                parent=self,
            )
            return
        self.open_conversation(conversation)

    # BUYER / SELLER WINDOW: shows the signed-in user's conversations.
    def page_messages(self):
        self.page_heading(
            "Messages",
            "Talk with buyers and sellers about vehicle listings.",
        )
        rows = ctk.CTkScrollableFrame(
            self.content, fg_color=COLORS["card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        rows.pack(fill="both", expand=True)
        try:
            conversations = self.messaging_store.list_conversations(
                self.current_user["email"]
            )
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Messages", f"Could not load conversations: {exc}", parent=self
            )
            return
        if not conversations:
            ctk.CTkLabel(
                rows, text="No messages yet. Contact a seller from a car listing.",
                text_color=COLORS["muted"],
            ).pack(padx=20, pady=24)
            return
        for conversation in conversations:
            partner = (
                conversation["buyer_name"]
                if conversation["seller_email"] == self.current_user["email"]
                else conversation["seller_name"]
            )
            preview = conversation["last_message"] or "Start the conversation"
            row = ctk.CTkFrame(
                rows, fg_color=COLORS["ivory"], corner_radius=10
            )
            row.pack(fill="x", padx=10, pady=6)
            summary = ctk.CTkFrame(row, fg_color="transparent")
            summary.pack(side="left", fill="x", expand=True, padx=12, pady=10)
            ctk.CTkLabel(
                summary,
                text=f'{partner}  ·  {conversation["model"]} {conversation["year"]}',
                anchor="w", font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["text"],
            ).pack(anchor="w")
            ctk.CTkLabel(
                summary, text=preview[:110], anchor="w",
                text_color=COLORS["muted"],
            ).pack(anchor="w", pady=(3, 0))
            ctk.CTkButton(
                row, text="Open", width=75, fg_color=COLORS["olive"],
                hover_color=COLORS["olive_hover"],
                command=lambda item=conversation: self.open_conversation(item),
            ).pack(side="right", padx=12, pady=10)

    # BUYER / SELLER CHAT WINDOW: displays and refreshes a conversation.
    def open_conversation(self, conversation):
        current_email = self.current_user["email"]
        is_seller = conversation["seller_email"] == current_email
        partner_name = (
            conversation["buyer_name"] if is_seller
            else conversation["seller_name"]
        )
        win = ctk.CTkToplevel(self)
        win.title(f'Messages | {partner_name}')
        win.geometry("620x640")
        win.minsize(440, 420)
        win.configure(fg_color=COLORS["ivory"])
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            win,
            text=f'{partner_name}  ·  {conversation["model"]} {conversation["year"]}',
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=COLORS["maroon"],
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        message_list = ctk.CTkScrollableFrame(
            win, fg_color=COLORS["card"], corner_radius=10,
        )
        message_list.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        composer = ctk.CTkFrame(win, fg_color="transparent")
        composer.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        composer.grid_columnconfigure(0, weight=1)
        message_entry = ctk.CTkEntry(
            composer, placeholder_text="Write a message...",
            height=38, fg_color=COLORS["card"],
        )
        message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        status = ctk.CTkLabel(
            win, text="Messages refresh automatically.",
            text_color=COLORS["muted"],
        )
        status.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 8))

        refresh_state = {"after_id": None, "last_message_id": None, "closed": False}

        def refresh_messages(schedule_next=True):
            if refresh_state["closed"]:
                return
            try:
                messages = self.messaging_store.list_messages(
                    conversation["id"], current_email
                )
            except (ValueError, sqlite3.Error) as exc:
                status.configure(text=f"Could not refresh messages: {exc}")
            else:
                latest_id = messages[-1]["id"] if messages else None
                if latest_id != refresh_state["last_message_id"]:
                    for widget in message_list.winfo_children():
                        widget.destroy()
                    if not messages:
                        ctk.CTkLabel(
                            message_list, text="Say hello to start the conversation.",
                            text_color=COLORS["muted"],
                        ).pack(padx=14, pady=20)
                    for message in messages:
                        own_message = message["sender_email"] == current_email
                        bubble = ctk.CTkFrame(
                            message_list,
                            fg_color=COLORS["pale_green"] if own_message
                            else COLORS["ivory"],
                            corner_radius=10,
                        )
                        bubble.pack(
                            anchor="e" if own_message else "w",
                            padx=10, pady=5,
                        )
                        ctk.CTkLabel(
                            bubble, text=message["body"], justify="left",
                            wraplength=400, text_color=COLORS["text"],
                        ).pack(anchor="w", padx=10, pady=(7, 2))
                        ctk.CTkLabel(
                            bubble, text=message["created_at"],
                            font=ctk.CTkFont(size=9),
                            text_color=COLORS["muted"],
                        ).pack(anchor="e", padx=10, pady=(0, 5))
                    message_list._parent_canvas.yview_moveto(1.0)
                    refresh_state["last_message_id"] = latest_id
            if schedule_next and not refresh_state["closed"]:
                refresh_state["after_id"] = win.after(
                    1000, refresh_messages
                )

        def send_message(_event=None):
            body = message_entry.get().strip()
            if not body:
                return
            try:
                self.messaging_store.send_message(
                    conversation["id"], current_email, body
                )
            except (ValueError, sqlite3.Error) as exc:
                status.configure(text=f"Could not send message: {exc}")
                return
            message_entry.delete(0, "end")
            refresh_messages(schedule_next=False)

        def close_chat():
            refresh_state["closed"] = True
            if refresh_state["after_id"] is not None:
                win.after_cancel(refresh_state["after_id"])
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", close_chat)
        ctk.CTkButton(
            composer, text="Send", width=80, height=38,
            fg_color=COLORS["maroon"], hover_color=COLORS["maroon_hover"],
            command=send_message,
        ).grid(row=0, column=1)
        message_entry.bind("<Return>", send_message)
        refresh_messages()

    # BUYER WINDOW: displays the vehicle comparison page.
    def page_compare(self):
        self.page_heading("Compare Cars", "Compare prices and specifications.")
        ctk.CTkLabel(self.content, text="Choose cars from Browse Cars to inspect their details. Side-by-side comparison can be expanded in the next development phase.",
                     text_color=COLORS["muted"], wraplength=700).pack(anchor="w")
        self.car_grid(self.content, self.cars[:4])
