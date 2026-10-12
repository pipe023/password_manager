import gc
import os
import secrets
import string
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import pyperclip

from vault import Vault

if getattr(sys, "frozen", False):
    app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    vault_directory = app_data / "PyManager"
    vault_directory.mkdir(parents=True, exist_ok=True)
    VAULT_PATH = str(vault_directory / "my_vault.enc")
else:
    VAULT_PATH = "my_vault.enc"
CLIPBOARD_TIMEOUT = 15
AUTO_LOCK_TIMEOUT = 5 * 60 * 1000
MIN_GENERATED_PASSWORD_LENGTH = 8
MAX_GENERATED_PASSWORD_LENGTH = 128
DEFAULT_GENERATED_PASSWORD_LENGTH = 20


class PasswordManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PyManager | Password Vault")
        self.root.geometry("900x620")
        self.root.minsize(420, 360)
        self.root.configure(background="#0b1120")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.colors = {
            "background": "#0b1120",
            "surface": "#111a2e",
            "surface_light": "#18243b",
            "border": "#263550",
            "text": "#e7edf7",
            "muted": "#94a3b8",
            "accent": "#6d8cff",
            "accent_hover": "#829cff",
            "danger": "#ff7185",
        }
        logo_path = Path(__file__).resolve().parent / "assets" / "pymanager_logo.png"
        if not logo_path.is_file():
            raise FileNotFoundError(f"Application logo not found: {logo_path}")
        self.logo_image = tk.PhotoImage(file=str(logo_path)).subsample(10, 10)
        self.root.iconphoto(True, self.logo_image)
        self._clipboard_value = None
        self._clipboard_after = None
        self._idle_after = None
        self._entry_windows = set()
        self.vault = Vault(VAULT_PATH)
        self.current_frame = None
        self._content_window = None
        self._vertical_scrollbar_visible = True
        self._horizontal_scrollbar_visible = True

        self._configure_styles()
        self._configure_scrollable_content()
        self.root.bind_all("<KeyPress>", self._reset_idle_lock, add="+")
        self.root.bind_all("<ButtonPress>", self._reset_idle_lock, add="+")
        self.root.bind_all("<Motion>", self._reset_idle_lock, add="+")
        self.root.bind_all("<MouseWheel>", self._scroll_content, add="+")
        self.root.bind_all("<Shift-MouseWheel>", self._scroll_content_horizontally, add="+")
        self.root.bind_all("<Button-4>", self._scroll_content, add="+")
        self.root.bind_all("<Button-5>", self._scroll_content, add="+")
        self.show_login_screen()

    def _configure_scrollable_content(self):
        container = tk.Frame(self.root, background=self.colors["background"])
        container.pack(fill=tk.BOTH, expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.content_canvas = tk.Canvas(
            container,
            background=self.colors["background"],
            borderwidth=0,
            highlightthickness=0,
        )
        self.content_canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar = ttk.Scrollbar(
            container,
            orient=tk.VERTICAL,
            command=self.content_canvas.yview,
        )
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar = ttk.Scrollbar(
            container,
            orient=tk.HORIZONTAL,
            command=self.content_canvas.xview,
        )
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.content_canvas.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )
        self.content_canvas.bind("<Configure>", self._resize_scrollable_content)

    def _resize_scrollable_content(self, _event=None):
        if self.current_frame is None or self._content_window is None:
            return
        requested_width = self.current_frame.winfo_reqwidth()
        requested_height = self.current_frame.winfo_reqheight()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        needs_vertical_scroll = requested_height > canvas_height
        needs_horizontal_scroll = requested_width > canvas_width
        self._set_scrollbar_visibility(
            self.vertical_scrollbar, needs_vertical_scroll, vertical=True
        )
        self._set_scrollbar_visibility(
            self.horizontal_scrollbar, needs_horizontal_scroll, vertical=False
        )
        self.content_canvas.itemconfigure(
            self._content_window,
            width=max(requested_width, canvas_width),
            height=max(requested_height, canvas_height),
        )
        self.content_canvas.configure(
            scrollregion=(
                0,
                0,
                max(requested_width, canvas_width),
                max(requested_height, canvas_height),
            )
        )

    def _set_scrollbar_visibility(self, scrollbar, visible, *, vertical):
        attribute = (
            "_vertical_scrollbar_visible"
            if vertical
            else "_horizontal_scrollbar_visible"
        )
        if getattr(self, attribute) == visible:
            return
        if visible:
            scrollbar.grid()
        else:
            scrollbar.grid_remove()
        setattr(self, attribute, visible)

    def _scroll_content(self, event):
        if not self._pointer_is_over_content(event.widget):
            return
        if getattr(event, "state", 0) & 0x0001:
            return
        if getattr(event, "num", None) == 4:
            amount = -1
        elif getattr(event, "num", None) == 5:
            amount = 1
        else:
            amount = -int(event.delta / 120)
        if amount:
            self.content_canvas.yview_scroll(amount, "units")

    def _scroll_content_horizontally(self, event):
        if self._pointer_is_over_content(event.widget):
            amount = -int(event.delta / 120)
            if amount:
                self.content_canvas.xview_scroll(amount, "units")

    def _pointer_is_over_content(self, widget):
        while widget is not None:
            if widget is self.content_canvas:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _configure_styles(self):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        c = self.colors
        style.configure(".", font=("Segoe UI", 10))
        style.configure("App.TFrame", background=c["background"])
        style.configure("Card.TFrame", background=c["surface"])
        style.configure("App.TLabel", background=c["background"], foreground=c["text"])
        style.configure("Card.TLabel", background=c["surface"], foreground=c["text"])
        style.configure("Muted.TLabel", background=c["surface"], foreground=c["muted"])
        style.configure(
            "Title.TLabel",
            background=c["background"],
            foreground=c["text"],
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "DialogTitle.TLabel",
            background=c["background"],
            foreground=c["text"],
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "Accent.TButton",
            background=c["accent"],
            foreground="#ffffff",
            padding=(14, 9),
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", c["accent_hover"]), ("disabled", c["border"])],
            foreground=[("disabled", c["muted"]), ("!disabled", "#ffffff")],
        )
        style.configure(
            "App.TButton",
            background=c["surface_light"],
            foreground=c["text"],
            padding=(12, 8),
            borderwidth=0,
        )
        style.map(
            "App.TButton",
            background=[("active", c["border"])],
            foreground=[("disabled", c["muted"]), ("!disabled", c["text"])],
        )
        style.configure(
            "App.TCheckbutton",
            background=c["surface"],
            foreground=c["muted"],
        )
        style.map("App.TCheckbutton", background=[("active", c["surface"])])
        style.configure(
            "Danger.TButton",
            background=c["surface_light"],
            foreground=c["danger"],
            padding=(12, 8),
            borderwidth=0,
        )
        style.map(
            "Danger.TButton",
            background=[("active", c["border"])],
            foreground=[("disabled", c["muted"]), ("!disabled", c["danger"])],
        )
        style.configure(
            "App.TEntry",
            fieldbackground=c["surface_light"],
            foreground=c["text"],
            insertcolor=c["text"],
            padding=9,
            borderwidth=1,
        )
        style.configure(
            "App.Treeview",
            background=c["surface"],
            fieldbackground=c["surface"],
            foreground=c["text"],
            rowheight=38,
            borderwidth=0,
        )
        style.configure(
            "App.Treeview.Heading",
            background=c["surface_light"],
            foreground=c["muted"],
            padding=(10, 10),
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "App.Treeview",
            background=[("selected", "#293b62")],
            foreground=[("selected", "#ffffff")],
        )

    def clear_frame(self):
        if self.current_frame:
            self.content_canvas.delete(self._content_window)
            self.current_frame.destroy()
        self.current_frame = ttk.Frame(
            self.content_canvas, style="App.TFrame", padding=28
        )
        self._content_window = self.content_canvas.create_window(
            (0, 0),
            window=self.current_frame,
            anchor=tk.NW,
        )
        self.current_frame.bind(
            "<Configure>", self._resize_scrollable_content
        )
        self.content_canvas.xview_moveto(0)
        self.content_canvas.yview_moveto(0)
        self._resize_scrollable_content()

    def _header(self, parent, subtitle):
        header = ttk.Frame(parent, style="App.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            image=self.logo_image,
            style="App.TLabel",
        ).pack(side=tk.LEFT, padx=(0, 14))
        text = ttk.Frame(header, style="App.TFrame")
        text.pack(side=tk.LEFT, fill=tk.Y, pady=4)
        ttk.Label(text, text="PyManager", style="Title.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(text, text=subtitle, style="App.TLabel").pack(
            anchor=tk.W, pady=(4, 0)
        )

    def show_login_screen(self):
        self._cancel_idle_lock()
        self.clear_frame()
        self._header(
            self.current_frame,
            "Powered by Information Systems Group",
        )

        card = ttk.Frame(self.current_frame, style="Card.TFrame", padding=28)
        card.pack(expand=True, fill=tk.X, padx=70, pady=28)
        initialized = self.vault.is_initialized()
        heading = "Welcome back" if initialized else "Create your vault"
        hint = (
            "Unlock your encrypted vault to continue."
            if initialized
            else "Choose a strong master password. Use at least 12 characters."
        )
        ttk.Label(card, text=heading, style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(card, text=hint, style="Muted.TLabel", wraplength=500).pack(
            anchor=tk.W, pady=(6, 22)
        )

        self.pwd_entry = ttk.Entry(card, style="App.TEntry", show="*")
        self.pwd_entry.pack(fill=tk.X)
        self.pwd_entry.bind("<Return>", lambda _event: self.authenticate())
        self.pwd_entry.focus_set()

        self.show_master_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            card,
            text="Show master password",
            variable=self.show_master_var,
            style="App.TCheckbutton",
            command=lambda: self._toggle_entry_visibility(
                self.pwd_entry, self.show_master_var.get()
            ),
        ).pack(anchor=tk.W, pady=(8, 12))

        self.pwd_confirm = None
        if initialized:
            ttk.Button(
                card,
                text="Unlock vault",
                style="Accent.TButton",
                command=self.authenticate,
            ).pack(fill=tk.X, pady=(8, 0))
        else:
            ttk.Label(card, text="Confirm master password", style="Muted.TLabel").pack(
                anchor=tk.W, pady=(2, 6)
            )
            self.pwd_confirm = ttk.Entry(card, style="App.TEntry", show="*")
            self.pwd_confirm.pack(fill=tk.X)
            self.pwd_confirm.bind(
                "<Return>", lambda _event: self.initialize_vault()
            )
            ttk.Button(
                card,
                text="Create encrypted vault",
                style="Accent.TButton",
                command=self.initialize_vault,
            ).pack(fill=tk.X, pady=(18, 0))

        ttk.Label(
            self.current_frame,
            text="Encrypted locally • Auto-locks after 5 minutes of inactivity",
            style="App.TLabel",
        ).pack(anchor=tk.CENTER, pady=(4, 0))

    @staticmethod
    def _toggle_entry_visibility(entry, visible):
        entry.configure(show="" if visible else "*")

    def authenticate(self):
        password = self.pwd_entry.get()
        if not password:
            messagebox.showwarning(
                "Master password required",
                "Enter your master password to unlock the vault.",
                parent=self.root,
            )
            return
        try:
            self.vault.unlock(password)
        except (ValueError, KeyError, OSError, TypeError):
            messagebox.showerror(
                "Unable to unlock",
                "The master password is incorrect or the vault data is corrupted.",
                parent=self.root,
            )
            self.pwd_entry.delete(0, tk.END)
            return
        self.pwd_entry.delete(0, tk.END)
        self.show_main_screen()

    def initialize_vault(self):
        password = self.pwd_entry.get()
        confirmation = self.pwd_confirm.get() if self.pwd_confirm else ""
        if len(password) < 12:
            messagebox.showwarning(
                "Master password too short",
                "Use at least 12 characters. A memorable multi-word passphrase is a good choice.",
                parent=self.root,
            )
            return
        if password != confirmation:
            messagebox.showerror(
                "Passwords do not match",
                "Enter the same master password in both fields.",
                parent=self.root,
            )
            self.pwd_confirm.delete(0, tk.END)
            return
        try:
            self.vault.initialize(password)
        except (OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                "Vault creation failed",
                f"The encrypted vault could not be created:\n{error}",
                parent=self.root,
            )
            return
        self.pwd_entry.delete(0, tk.END)
        if self.pwd_confirm:
            self.pwd_confirm.delete(0, tk.END)
        self.show_main_screen()

    def show_main_screen(self):
        self.clear_frame()
        self._header(self.current_frame, "A safer home for your digital life.")

        toolbar = ttk.Frame(self.current_frame, style="App.TFrame")
        toolbar.pack(fill=tk.X, pady=(22, 14))
        ttk.Label(toolbar, text="Search", style="App.TLabel").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.refresh_list)
        search = ttk.Entry(
            toolbar, textvariable=self.search_var, style="App.TEntry"
        )
        search.pack(side=tk.LEFT, padx=(10, 14), fill=tk.X, expand=True)
        ttk.Button(toolbar, text="Lock now", style="App.TButton", command=self.lock_vault).pack(
            side=tk.RIGHT
        )

        card = ttk.Frame(self.current_frame, style="Card.TFrame", padding=16)
        card.pack(fill=tk.BOTH, expand=True)
        list_header = ttk.Frame(card, style="Card.TFrame")
        list_header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(list_header, text="Your items", style="Section.TLabel").pack(
            side=tk.LEFT
        )
        self.count_label = ttk.Label(list_header, text="", style="Muted.TLabel")
        self.count_label.pack(side=tk.RIGHT)

        table_frame = ttk.Frame(card, style="Card.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("site", "username")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="App.Treeview",
        )
        self.tree.heading("site", text="SERVICE")
        self.tree.heading("username", text="USERNAME")
        self.tree.column("site", width=250, anchor=tk.W)
        self.tree.column("username", width=250, anchor=tk.W)
        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", lambda _event: self.view_entry())

        actions = ttk.Frame(self.current_frame, style="App.TFrame")
        actions.pack(fill=tk.X, pady=(14, 0))
        ttk.Button(
            actions, text="＋  Add item", style="Accent.TButton", command=self.add_entry
        ).pack(side=tk.LEFT)
        ttk.Button(
            actions, text="View / edit", style="App.TButton", command=self.view_entry
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(
            actions, text="Delete", style="Danger.TButton", command=self.delete_entry
        ).pack(side=tk.LEFT)
        ttk.Label(
            actions, text="Auto-lock in 5 minutes of inactivity", style="App.TLabel"
        ).pack(side=tk.RIGHT)

        self._reset_idle_lock()
        self.refresh_list()
        search.focus_set()

    def refresh_list(self, *_args):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = self.search_var.get().casefold().strip()
        visible_count = 0
        for entry_id, data in self.vault.entries.items():
            site = str(data.get("site", ""))
            username = str(data.get("username", ""))
            if query in site.casefold() or query in username.casefold():
                self.tree.insert(
                    "", tk.END, iid=entry_id, values=(site, username)
                )
                visible_count += 1
        total = len(self.vault.entries)
        self.count_label.configure(
            text=f"{visible_count} shown" if query else f"{total} item{'s' if total != 1 else ''}"
        )

    def add_entry(self):
        self.open_entry_window(title="Add item")

    def view_entry(self):
        selected = self.tree.selection()
        if not selected:
            return
        entry_id = selected[0]
        data = self.vault.entries.get(entry_id)
        if data is None:
            return
        self.open_entry_window(
            title="View / edit item", entry_id=entry_id, existing_data=data
        )

    def delete_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(
                "Select an item", "Choose an item to delete.", parent=self.root
            )
            return
        if messagebox.askyesno(
            "Delete item",
            "Permanently delete the selected item?",
            parent=self.root,
        ):
            entry_id = selected[0]
            previous_data = self.vault.entries.get(entry_id)
            try:
                self.vault.delete_entry(entry_id)
            except (OSError, RuntimeError, ValueError) as error:
                if previous_data is not None:
                    self.vault.entries[entry_id] = previous_data
                messagebox.showerror(
                    "Delete failed", f"The item could not be deleted:\n{error}", parent=self.root
                )
                return
            self.refresh_list()

    def copy_password(self, password):
        try:
            pyperclip.copy(password)
        except pyperclip.PyperclipException as error:
            messagebox.showerror(
                "Clipboard unavailable",
                f"The password could not be copied:\n{error}",
                parent=self.root,
            )
            return

        self._clipboard_value = password
        if self._clipboard_after is not None:
            self.root.after_cancel(self._clipboard_after)
        self._clipboard_after = self.root.after(
            CLIPBOARD_TIMEOUT * 1000, self._clear_clipboard_if_unchanged
        )
        messagebox.showinfo(
            "Password copied",
            f"Clipboard will be cleared in {CLIPBOARD_TIMEOUT} seconds.",
            parent=self.root,
        )

    def _clear_clipboard_if_unchanged(self):
        self._clipboard_after = None
        if self._clipboard_value is None:
            return
        try:
            if pyperclip.paste() == self._clipboard_value:
                pyperclip.copy("")
        except pyperclip.PyperclipException as error:
            messagebox.showwarning(
                "Clipboard could not be cleared",
                f"Clear it manually to protect the copied password:\n{error}",
                parent=self.root,
            )
        finally:
            self._clipboard_value = None

    def _clear_clipboard_now(self):
        if self._clipboard_after is not None:
            self.root.after_cancel(self._clipboard_after)
            self._clipboard_after = None
        if self._clipboard_value is None:
            return
        try:
            if pyperclip.paste() == self._clipboard_value:
                pyperclip.copy("")
        except pyperclip.PyperclipException:
            messagebox.showwarning(
                "Clipboard may still contain a password",
                "The clipboard could not be checked or cleared. Clear it manually.",
                parent=self.root,
            )
        finally:
            self._clipboard_value = None

    def _close_entry_windows(self):
        for win in tuple(self._entry_windows):
            win.destroy()
        self._entry_windows.clear()

    def open_entry_window(self, title, entry_id=None, existing_data=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(background=self.colors["background"])
        win.geometry("500x530")
        win.minsize(420, 460)
        win.transient(self.root)
        win.grab_set()
        self._entry_windows.add(win)

        def close_window():
            self._entry_windows.discard(win)
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", close_window)

        form = ttk.Frame(win, style="App.TFrame", padding=24)
        form.pack(fill=tk.BOTH, expand=True)
        ttk.Label(form, text=title, style="DialogTitle.TLabel").pack(
            anchor=tk.W, pady=(0, 18)
        )

        ttk.Label(form, text="Service", style="App.TLabel").pack(
            anchor=tk.W, pady=(0, 5)
        )
        site_ent = ttk.Entry(form, style="App.TEntry")
        site_ent.pack(fill=tk.X, pady=(0, 14))

        ttk.Label(form, text="Username or email", style="App.TLabel").pack(
            anchor=tk.W, pady=(0, 5)
        )
        user_ent = ttk.Entry(form, style="App.TEntry")
        user_ent.pack(fill=tk.X, pady=(0, 14))

        ttk.Label(form, text="Password", style="App.TLabel").pack(
            anchor=tk.W, pady=(0, 5)
        )
        pwd_frame = ttk.Frame(form, style="App.TFrame")
        pwd_frame.pack(fill=tk.X)
        pwd_ent = ttk.Entry(pwd_frame, style="App.TEntry", show="*")
        pwd_ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        show_pwd_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pwd_frame,
            text="Show",
            variable=show_pwd_var,
            style="App.TCheckbutton",
            command=lambda: self._toggle_entry_visibility(
                pwd_ent, show_pwd_var.get()
            ),
        ).pack(side=tk.LEFT, padx=(10, 0))

        pwd_actions = ttk.Frame(form, style="App.TFrame")
        pwd_actions.pack(fill=tk.X, pady=(8, 14))
        ttk.Button(
            pwd_actions,
            text="Generate password",
            style="App.TButton",
            command=lambda: self._generate_password(
                pwd_ent, show_pwd_var, length_var.get()
            ),
        ).pack(side=tk.LEFT)
        ttk.Button(
            pwd_actions,
            text="Copy password",
            style="App.TButton",
            command=lambda: self.copy_password(pwd_ent.get()),
        ).pack(side=tk.LEFT, padx=(8, 14))
        ttk.Label(
            pwd_actions,
            text=f"Length ({MIN_GENERATED_PASSWORD_LENGTH}-{MAX_GENERATED_PASSWORD_LENGTH})",
            style="App.TLabel",
        ).pack(side=tk.LEFT, padx=(0, 6))
        length_var = tk.StringVar(value=str(DEFAULT_GENERATED_PASSWORD_LENGTH))
        ttk.Spinbox(
            pwd_actions,
            from_=MIN_GENERATED_PASSWORD_LENGTH,
            to=MAX_GENERATED_PASSWORD_LENGTH,
            textvariable=length_var,
            width=5,
            wrap=True,
        ).pack(side=tk.LEFT)
        ttk.Label(
            form,
            text="Notes",
            style="App.TLabel",
        ).pack(anchor=tk.W, pady=(0, 5))
        notes_ent = tk.Text(
            form,
            height=5,
            wrap=tk.WORD,
            background=self.colors["surface_light"],
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT,
            padx=9,
            pady=8,
            font=("Segoe UI", 10),
        )
        notes_ent.pack(fill=tk.BOTH, expand=True)

        if existing_data:
            site_ent.insert(0, existing_data.get("site", ""))
            user_ent.insert(0, existing_data.get("username", ""))
            pwd_ent.insert(0, existing_data.get("password", ""))
            notes_ent.insert("1.0", existing_data.get("notes", ""))

        def save():
            site = site_ent.get().strip()
            user = user_ent.get().strip()
            password = pwd_ent.get()
            notes = notes_ent.get("1.0", "end-1c")
            if not site or not password:
                messagebox.showwarning(
                    "Required fields",
                    "A service name and password are required.",
                    parent=win,
                )
                return
            previous_ids = set(self.vault.entries)
            previous_data = self.vault.entries.get(entry_id) if entry_id else None
            try:
                if entry_id:
                    self.vault.entries[entry_id] = {
                        "site": site,
                        "username": user,
                        "password": password,
                        "notes": notes,
                    }
                    self.vault._save()
                else:
                    self.vault.add_entry(site, user, password, notes)
            except (OSError, RuntimeError, ValueError) as error:
                if entry_id and previous_data is not None:
                    self.vault.entries[entry_id] = previous_data
                elif not entry_id:
                    for new_id in set(self.vault.entries) - previous_ids:
                        self.vault.entries.pop(new_id, None)
                messagebox.showerror(
                    "Save failed",
                    f"The encrypted vault could not be saved:\n{error}",
                    parent=win,
                )
                return
            self.refresh_list()
            close_window()

        footer = ttk.Frame(form, style="App.TFrame")
        footer.pack(fill=tk.X, pady=(14, 0))
        tk.Button(
            footer,
            text="Cancel",
            command=close_window,
            background=self.colors["surface_light"],
            foreground=self.colors["text"],
            activebackground=self.colors["border"],
            activeforeground=self.colors["text"],
            disabledforeground=self.colors["muted"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=18,
            pady=9,
            font=("Segoe UI", 10),
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            footer,
            text="Save item",
            command=save,
            background=self.colors["accent"],
            foreground="#ffffff",
            activebackground=self.colors["accent_hover"],
            activeforeground="#ffffff",
            disabledforeground=self.colors["muted"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=18,
            pady=9,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        ).pack(side=tk.RIGHT)
        site_ent.focus_set()

    def _generate_password(self, entry, show_var, length):
        try:
            length = int(length)
        except (TypeError, ValueError):
            messagebox.showwarning(
                "Invalid password length",
                f"Choose a length from {MIN_GENERATED_PASSWORD_LENGTH} to "
                f"{MAX_GENERATED_PASSWORD_LENGTH} characters.",
                parent=entry.winfo_toplevel(),
            )
            return
        if not MIN_GENERATED_PASSWORD_LENGTH <= length <= MAX_GENERATED_PASSWORD_LENGTH:
            messagebox.showwarning(
                "Password length out of range",
                f"Choose a length from {MIN_GENERATED_PASSWORD_LENGTH} to "
                f"{MAX_GENERATED_PASSWORD_LENGTH} characters.",
                parent=entry.winfo_toplevel(),
            )
            return
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        entry.delete(0, tk.END)
        entry.insert(0, password)
        show_var.set(True)
        entry.configure(show="")

    def _reset_idle_lock(self, _event=None):
        if self.current_frame is None or not self.vault.key:
            return
        self._cancel_idle_lock()
        self._idle_after = self.root.after(AUTO_LOCK_TIMEOUT, self.lock_vault)

    def _cancel_idle_lock(self):
        if self._idle_after is not None:
            self.root.after_cancel(self._idle_after)
            self._idle_after = None

    def lock_vault(self):
        self._cancel_idle_lock()
        self._clear_clipboard_now()
        self._close_entry_windows()
        self.vault.lock()
        gc.collect()
        self.show_login_screen()

    def close(self):
        self._cancel_idle_lock()
        self._clear_clipboard_now()
        self._close_entry_windows()
        self.vault.lock()
        gc.collect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordManagerGUI(root)
    root.mainloop()
