import customtkinter as ctk
from tkinter import filedialog, messagebox
import math
import os
import sqlite3
import shutil
import uuid
from PIL import Image, ImageOps

from .buyer import listings_for_seller
from .common import COLORS


MAX_CAR_PHOTO_BYTES = 10 * 1024 * 1024
CAR_PHOTO_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
}


def validate_car_photo(path):
    if not os.path.isfile(path):
        raise ValueError("Choose an image file that still exists.")
    if os.path.getsize(path) > MAX_CAR_PHOTO_BYTES:
        raise ValueError("Choose an image smaller than 10 MB.")
    with Image.open(path) as photo:
        if photo.format not in CAR_PHOTO_FORMATS:
            raise ValueError("Choose a JPEG, PNG, WEBP, or BMP image.")
        photo.verify()


def store_car_photo(source_path, destination_directory):
    validate_car_photo(source_path)
    with Image.open(source_path) as photo:
        extension = CAR_PHOTO_FORMATS[photo.format]
    os.makedirs(destination_directory, exist_ok=True)
    destination_path = os.path.join(
        destination_directory, f"{uuid.uuid4().hex}{extension}"
    )
    shutil.copy2(source_path, destination_path)
    return destination_path


class SellerPages:
    # SELLER WINDOW / ADD LISTING PAGE: builds the vehicle listing form.
    def page_add_car(self):
        self.page_heading("Add New Car Listing", "Enter vehicle information and upload a photo.")
        outer = ctk.CTkFrame(self.content, fg_color=COLORS["card"], corner_radius=12,
                             border_width=1, border_color=COLORS["border"])
        outer.pack(fill="both", expand=True)
        form = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=22, pady=18)
        form.grid_columnconfigure((0, 1), weight=1)
        self.car_entries = {}
        fields = [
            ("Model", "e.g. Vios 1.3 E"), ("Year", "e.g. 2021"),
            ("Price (₱)", "e.g. 720000"), ("Mileage (km)", "e.g. 32000"), ("Location", "e.g. Dagupan City"),
            ("Transmission", "e.g. Automatic"), ("Fuel Type", "e.g. Gasoline"),
            ("Body Type", "e.g. Sedan"), ("Condition", "e.g. Good"),
        ]
        for i, (label, placeholder) in enumerate(fields):
            r, col = divmod(i, 2)
            ctk.CTkLabel(form, text=label, text_color=COLORS["text"], font=ctk.CTkFont(size=12, weight="bold")).grid(row=r*2, column=col, sticky="w", padx=8, pady=(4, 4))
            entry = ctk.CTkEntry(form, placeholder_text=placeholder, height=36, fg_color=COLORS["ivory"], border_color=COLORS["border"])
            entry.grid(row=r*2+1, column=col, sticky="ew", padx=8, pady=(0, 10))
            self.car_entries[label] = entry
        r = len(fields)
        ctk.CTkLabel(form, text="Description", text_color=COLORS["text"], font=ctk.CTkFont(size=12, weight="bold")).grid(row=r*2, column=0, sticky="w", padx=8, pady=(3, 4))
        self.description_box = ctk.CTkTextbox(form, height=80, fg_color=COLORS["ivory"], border_color=COLORS["border"], border_width=1)
        self.description_box.grid(row=r*2+1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 10))
        photo_row = ctk.CTkFrame(form, fg_color="transparent")
        photo_row.grid(row=(r * 2) + 2, column=0, columnspan=2, sticky="ew", padx=8, pady=5)
        self.car_photo_preview = ctk.CTkLabel(
            photo_row, text="No car photo selected", width=180, height=100,
            fg_color=COLORS["ivory"], text_color=COLORS["muted"],
            corner_radius=8,
        )
        self.car_photo_preview.pack(side="left", padx=(0, 15))
        self.car_photo_name = ctk.CTkLabel(
            photo_row, text="", text_color=COLORS["muted"]
        )
        self.car_photo_name.pack(side="left", padx=(0, 15))
        ctk.CTkButton(photo_row, text="Upload Car Photo", fg_color=COLORS["khaki"], hover_color=COLORS["olive"],
                      text_color=COLORS["text"], command=self.choose_photo).pack(side="left")
        bottom = ctk.CTkFrame(outer, fg_color="transparent")
        bottom.pack(fill="x", padx=25, pady=(0, 18))
        self.submit_listing_button = ctk.CTkButton(
            bottom, text="Submit Listing", height=42, fg_color=COLORS["olive"],
            hover_color=COLORS["olive_hover"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self.save_car
        )
        self.submit_listing_button.pack(side="right", padx=(8, 0))
        ctk.CTkButton(bottom, text="Cancel", height=40, fg_color=COLORS["khaki"], hover_color=COLORS["olive"],
                      text_color=COLORS["text"], command=lambda: self.show_page("My Listings")).pack(side="right")

    # SELLER WINDOW / ADD LISTING PAGE: chooses and previews a vehicle photo.
    def choose_photo(self):
        path = filedialog.askopenfilename(
            title="Choose car photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp")],
            parent=self,
        )
        if not path:
            return
        try:
            validate_car_photo(path)
            with Image.open(path) as photo:
                preview = ImageOps.contain(photo.convert("RGB"), (180, 100))
                self.car_photo_image = ctk.CTkImage(
                    light_image=preview,
                    dark_image=preview,
                    size=preview.size,
                )
        except (OSError, ValueError) as exc:
            messagebox.showerror("Invalid car photo", str(exc), parent=self)
            return
        self.photo_path = path
        self.car_photo_preview.configure(image=self.car_photo_image, text="")
        self.car_photo_name.configure(text=os.path.basename(path))

    # SELLER WINDOW / ADD LISTING PAGE: validates and saves a vehicle listing.
    def save_car(self):
        if getattr(self, "_submitting_listing", False):
            return
        self._submitting_listing = True
        self.submit_listing_button.configure(state="disabled")

        def reject_submission(title, message):
            self._submitting_listing = False
            self.submit_listing_button.configure(state="normal")
            messagebox.showerror(title, message, parent=self)

        data = {label: entry.get().strip() for label, entry in self.car_entries.items()}
        required = [
            "Model", "Year", "Price (₱)", "Mileage (km)", "Location",
            "Transmission", "Fuel Type", "Body Type", "Condition",
        ]
        missing = [field for field in required if not data[field]]
        if missing:
            reject_submission(
                "Missing information",
                "Please complete all required fields: " + ", ".join(missing) + "."
            )
            return
        try:
            price = float(data["Price (₱)"])
        except ValueError:
            reject_submission("Invalid price", "Enter a valid numeric price.")
            return
        if not math.isfinite(price) or price <= 0:
            reject_submission("Invalid price", "Price must be a number greater than zero.")
            return
        try:
            year = int(data["Year"])
        except ValueError:
            reject_submission("Invalid year", "Enter the year as a whole number.")
            return
        if year < 1886 or year > 2100:
            reject_submission("Invalid year", "Enter a valid vehicle year.")
            return
        try:
            mileage = int(data["Mileage (km)"])
        except ValueError:
            reject_submission("Invalid mileage", "Enter mileage as a whole number.")
            return
        if mileage < 0:
            reject_submission("Invalid mileage", "Mileage cannot be negative.")
            return
        if not self.photo_path:
            reject_submission("Car photo required", "Upload a car photo before submitting.")
            return
        try:
            stored_photo_path = store_car_photo(
                self.photo_path, self.car_photo_directory
            )
        except (OSError, ValueError) as exc:
            reject_submission("Invalid car photo", str(exc))
            return
        car = {
            "model": data["Model"], "year": data["Year"],
            "price": data["Price (₱)"], "mileage": data["Mileage (km)"],
            "location": data["Location"], "transmission": data["Transmission"] or "Not specified",
            "fuel": data["Fuel Type"] or "Not specified", "body": data["Body Type"] or "Not specified",
            "condition": data["Condition"] or "Not specified",
            "description": self.description_box.get("1.0", "end").strip(),
            "photo": stored_photo_path,
            "seller_email": self.current_user["email"],
        }
        try:
            car["id"] = self.car_listing_store.add(car)
        except sqlite3.Error as exc:
            try:
                os.remove(stored_photo_path)
            except OSError:
                pass
            reject_submission(
                "Could not save listing",
                f"The car listing could not be saved to the local database: {exc}",
            )
            return
        self.cars.insert(0, car)
        self.photo_path = ""
        self.car_photo_image = None
        for entry in self.car_entries.values():
            entry.delete(0, "end")
        self.description_box.delete("1.0", "end")
        self.car_photo_preview.configure(image=None, text="No car photo selected")
        self.car_photo_name.configure(text="")
        messagebox.showinfo(
            "Listing submitted", "Your car listing was submitted successfully.",
            parent=self
        )
        self._submitting_listing = False
        self.show_page("Dashboard")

    # SELLER WINDOW / MY LISTINGS PAGE: displays this seller's own posts.
    def page_listings(self):
        self.page_heading("My Listings", "Manage the vehicles you have listed.")
        ctk.CTkButton(self.content, text="+ Add New Car", fg_color=COLORS["olive"], hover_color=COLORS["olive_hover"],
                      command=lambda: self.show_page("Add New Car")).pack(anchor="e", pady=(0, 10))
        seller_cars = listings_for_seller(
            self.cars, self.current_user["email"]
        )
        if not seller_cars:
            ctk.CTkLabel(
                self.content, text="You have not listed any vehicles yet.",
                text_color=COLORS["muted"],
            ).pack(pady=30)
        for car in seller_cars:
            row = ctk.CTkFrame(self.content, fg_color=COLORS["card"], corner_radius=10,
                               border_width=1, border_color=COLORS["border"])
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=f'{car["model"]} ({car["year"]})',
                         font=ctk.CTkFont(size=15, weight="bold"), text_color=COLORS["text"]).pack(side="left", padx=15, pady=14)
            ctk.CTkLabel(row, text=f'₱ {int(float(car["price"])):,.0f}', text_color=COLORS["olive"],
                         font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=12)
            ctk.CTkButton(row, text="View", width=70, fg_color=COLORS["olive"], hover_color=COLORS["olive_hover"],
                          command=lambda c=car: self.show_car_details(c)).pack(side="right", padx=10, pady=10)
            ctk.CTkButton(row, text="Delete", width=70, fg_color=COLORS["red"], hover_color=COLORS["red_hover"],
                          command=lambda c=car: self.delete_car(c)).pack(side="right", padx=4, pady=10)

    # SELLER WINDOW / MY LISTINGS PAGE: deletes one of the seller's posts.
    def delete_car(self, car):
        if messagebox.askyesno("Delete listing", "Are you sure you want to delete this car listing?"):
            try:
                deleted = self.car_listing_store.delete(car["id"])
            except sqlite3.Error as exc:
                messagebox.showerror(
                    "Delete listing",
                    f"The listing could not be deleted from the local database: {exc}",
                    parent=self,
                )
                return
            if deleted and car in self.cars:
                self.cars.remove(car)
            self.show_page("My Listings")

    # SELLER WINDOW / INQUIRIES PAGE: opens the shared buyer-seller inbox.
    def page_inquiries(self):
        self.page_messages()
