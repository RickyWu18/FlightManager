"""Main window for the Flight Manager application.

This module defines the primary GUI window, handling user input,
flight log display, and interaction with the database and file system.
"""

import datetime
import json
import math
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, Optional

from flight_manager import version
from flight_manager.database import DatabaseManager
from flight_manager.file_manager import FileManager
from flight_manager.ui.calendar import CalendarDialog
from flight_manager.ui.dialogs import (
    ChecklistSettingsDialog,
    ComparisonDialog,
    FlightDetailsDialog,
    IgnoreSettingsDialog,
    VehicleSettingsDialog,
)


def get_resource_path(relative_path: str) -> str:
    """Gets the absolute path to a resource, supporting both dev and PyInstaller.

    Args:
        relative_path: The relative path to the resource.

    Returns:
        The absolute path to the resource.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class FlightManagerApp:
    """The main application class for Flight Manager."""

    def __init__(self, root: tk.Tk):
        """Initializes the FlightManagerApp.

        Args:
            root: The root Tkinter window.
        """
        self.root = root
        self.root.title("Flight Manager Logger")
        self.root.geometry("1100x850")
        self.root.minsize(500, 400)

        # Set Window Icon
        icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            try:
                self.icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self.icon_img)
            except Exception:
                pass

        # Database Setup
        self.db = DatabaseManager()
        self.file_manager = FileManager()

        # State for Sorting/Filtering
        self.sort_col = "flight_no"
        self.sort_desc = False

        # Multi-Column Filter Vars
        self.filter_id = tk.StringVar()
        self.log_date_var = tk.StringVar(
            value=datetime.date.today().strftime("%Y-%m-%d")
        )
        self.filter_date = tk.StringVar(
            value=datetime.date.today().strftime("%Y-%m-%d")
        )
        self.filter_vehicle = tk.StringVar(value="All")

        # Pagination & Debounce State
        self.page = 0
        self.page_size = 50
        self._debounce_timer = None

        # Create Menu Bar
        self.create_menu()

        # GUI Layout
        self.create_widgets()

        # Initial Calculations
        self.calculate_next_id()

    def change_filter_date(self, days: int):
        """Changes the filter date by a specified number of days.

        Args:
            days: The number of days to shift (positive or negative).
        """
        try:
            current_str = self.filter_date.get()
            if not current_str:
                current_date = datetime.date.today()
            else:
                current_date = datetime.datetime.strptime(
                    current_str, "%Y-%m-%d"
                ).date()

            new_date = current_date + datetime.timedelta(days=days)
            self.filter_date.set(new_date.strftime("%Y-%m-%d"))
        except ValueError:
            # If current date is invalid, reset to today
            self.filter_date.set(datetime.date.today().strftime("%Y-%m-%d"))

    def pick_date(self, var: tk.StringVar, widget: tk.Widget = None):
        """Opens a calendar dialog to pick a date.

        Args:
            var: The StringVar to update with the selected date.
            widget: The widget to position the dialog relative to.
        """

        def on_date_selected(date_str: str):
            var.set(date_str)
            if var == self.log_date_var:
                self.calculate_next_id()

        CalendarDialog(self.root, on_date_selected, widget)

    def create_menu(self):
        """Creates the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(
            label="Manage Preflight Checklist",
            command=self.open_checklist_settings,
        )
        settings_menu.add_command(
            label="Manage Vehicles", command=self.open_vehicle_settings
        )
        settings_menu.add_command(
            label="Manage Ignore Patterns", command=self.open_ignore_settings
        )
        settings_menu.add_separator()
        settings_menu.add_command(
            label="Export Settings (JSON)", command=self.export_settings
        )
        settings_menu.add_command(
            label="Import Settings (JSON)", command=self.import_settings
        )
        menubar.add_cascade(label="Settings", menu=settings_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def show_about(self):
        """Displays the 'About' dialog."""
        msg = (
            f"{version.APP_NAME}\nVersion: {version.__version__}\n\n"
            f"{version.AUTHOR}\n{version.COPYRIGHT}"
        )
        messagebox.showinfo("About", msg)

    def export_settings(self):
        """Exports the current settings to a JSON file."""
        filename = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
        )
        if not filename:
            return

        try:
            settings = self.db.get_all_settings()
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", f"Settings exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror(
                "Export Error", f"Failed to export settings:\n{e}"
            )

    def import_settings(self):
        """Imports settings from a JSON file."""
        filename = filedialog.askopenfilename(
            title="Import Settings", filetypes=[("JSON Files", "*.json")]
        )
        if not filename:
            return

        confirm = messagebox.askyesno(
            "Confirm Import",
            "This will merge the imported settings with your current "
            "configuration.\n\n"
            "Existing Vehicles, Checklist Items, and Ignore Patterns will be "
            "preserved if they exist, but new ones will be added.\n\n"
            "Do you want to continue?",
        )
        if not confirm:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                settings = json.load(f)

            self.db.import_settings(settings)

            # Refresh UI elements that depend on settings
            self.refresh_vehicle_ui()
            self.refresh_checklist_ui()

            messagebox.showinfo("Success", "Settings imported successfully!")
        except Exception as e:
            messagebox.showerror(
                "Import Error", f"Failed to import settings:\n{e}"
            )

    def create_widgets(self):
        """Creates and arranges the main window widgets."""
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=4)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left Frame: Input ---
        self.input_frame = ttk.LabelFrame(
            main_pane, text="Log Entry", padding=(10, 10)
        )
        main_pane.add(self.input_frame, minsize=500)

        # Date
        ttk.Label(self.input_frame, text="Date (YYYY-MM-DD):").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.btn_date = ttk.Button(
            self.input_frame,
            textvariable=self.log_date_var,
        )
        self.btn_date.configure(
            command=lambda: self.pick_date(self.log_date_var, self.btn_date)
        )
        self.btn_date.grid(row=0, column=1, sticky="ew", pady=5)

        # Vehicle Name
        ttk.Label(self.input_frame, text="Vehicle:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.combo_vehicle = ttk.Combobox(self.input_frame, state="readonly")
        self.combo_vehicle.grid(row=1, column=1, sticky="ew", pady=5)

        # Flight ID
        ttk.Label(self.input_frame, text="Flight ID:").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.entry_flight_no = ttk.Entry(self.input_frame)
        self.entry_flight_no.grid(row=2, column=1, sticky="ew", pady=5)

        # Mission Title
        ttk.Label(self.input_frame, text="Mission Title:").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.entry_mission_title = ttk.Entry(self.input_frame)
        self.entry_mission_title.grid(row=3, column=1, sticky="ew", pady=5)

        # Preflight Check
        ttk.Label(self.input_frame, text="Preflight Check:").grid(
            row=4, column=0, sticky="nw", pady=5
        )

        self.checklist_canvas_frame = ttk.Frame(
            self.input_frame, borderwidth=1, relief="sunken"
        )
        self.checklist_canvas_frame.grid(
            row=4, column=1, columnspan=2, sticky="nsew", pady=5
        )

        self.canvas = tk.Canvas(
            self.checklist_canvas_frame,
            height=200,
            width=300,
        )
        scrollbar = ttk.Scrollbar(
            self.checklist_canvas_frame,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.checklist_frame = ttk.Frame(self.canvas)

        self.checklist_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        self.canvas.create_window(
            (0, 0), window=self.checklist_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.refresh_checklist_ui()

        # Parameter Section
        ttk.Label(self.input_frame, text="Parameter:").grid(
            row=5, column=0, sticky="nw", pady=5
        )

        param_frame = ttk.Frame(self.input_frame)
        param_frame.grid(row=5, column=1, columnspan=2, sticky="ew", pady=5)

        self.entry_param_file = ttk.Entry(param_frame)
        self.entry_param_file.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        self.entry_param_file.state(["readonly"])

        ttk.Button(
            param_frame, text="Browse...", command=self.browse_param_file
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            param_frame, text="Compare", command=self.compare_params_from_input
        ).pack(side=tk.LEFT, padx=2)

        # Flight Log Section
        ttk.Label(self.input_frame, text="Flight Log:").grid(
            row=6, column=0, sticky="nw", pady=5
        )

        log_frame = ttk.Frame(self.input_frame)
        log_frame.grid(row=6, column=1, columnspan=2, sticky="ew", pady=5)

        self.entry_log_file = ttk.Entry(log_frame)
        self.entry_log_file.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        self.entry_log_file.state(["readonly"])

        ttk.Button(
            log_frame, text="Browse...", command=self.browse_log_file
        ).pack(side=tk.LEFT, padx=2)

        # Note Section
        ttk.Label(self.input_frame, text="Note:").grid(
            row=7, column=0, sticky="nw", pady=5
        )
        self.text_note = scrolledtext.ScrolledText(
            self.input_frame, height=4, width=40, font=("Segoe UI", 9)
        )
        self.text_note.grid(
            row=7, column=1, columnspan=2, sticky="nsew", pady=5
        )

        # Buttons
        btn_frame = ttk.Frame(self.input_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=20)

        ttk.Button(btn_frame, text="Save Log", command=self.save_log).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_form).pack(
            side=tk.LEFT, padx=5
        )

        self.input_frame.columnconfigure(1, weight=1, minsize=300)
        self.input_frame.rowconfigure(4, weight=1)  # Checklist
        self.input_frame.rowconfigure(7, weight=1)  # Note

        # --- Right Frame: History ---
        self.history_frame = ttk.LabelFrame(
            main_pane,
            text="Flight History (Double-click for Details)",
            padding=(10, 10),
        )
        main_pane.add(self.history_frame)

        # Filter Bar
        filter_frame = ttk.Frame(self.history_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        # ID Filter
        ttk.Label(filter_frame, text="ID:").pack(side=tk.LEFT, padx=(0, 2))
        self.entry_filter_id = ttk.Entry(
            filter_frame, textvariable=self.filter_id, width=8
        )
        self.entry_filter_id.pack(side=tk.LEFT, padx=(0, 10))

        # Date Filter
        ttk.Label(filter_frame, text="Date:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(
            filter_frame,
            text="<",
            width=2,
            command=lambda: self.change_filter_date(-1),
        ).pack(side=tk.LEFT, padx=0)
        self.btn_filter_date = ttk.Button(
            filter_frame,
            textvariable=self.filter_date,
            width=10,
        )
        self.btn_filter_date.configure(
            command=lambda: self.pick_date(
                self.filter_date, self.btn_filter_date
            )
        )
        self.btn_filter_date.pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(
            filter_frame,
            text=">",
            width=2,
            command=lambda: self.change_filter_date(1),
        ).pack(side=tk.LEFT, padx=(0, 2))

        # Vehicle Filter
        ttk.Label(filter_frame, text="Vehicle:").pack(side=tk.LEFT, padx=(0, 2))
        self.combo_filter_vehicle = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_vehicle,
            state="readonly",
            width=15,
        )
        self.combo_filter_vehicle.pack(side=tk.LEFT, padx=(0, 10))

        # Auto-refresh triggers
        self.filter_id.trace(
            "w", lambda name, index, mode: self.load_logs_debounced()
        )
        self.filter_date.trace(
            "w", lambda name, index, mode: self.load_logs_debounced()
        )
        self.combo_filter_vehicle.bind(
            "<<ComboboxSelected>>", lambda e: self.load_logs_debounced()
        )

        ttk.Button(filter_frame, text="Reset", command=self.reset_filter).pack(
            side=tk.LEFT
        )

        # Pagination Controls
        self.pagination_frame = ttk.Frame(self.history_frame)
        self.pagination_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=2)

        self.btn_prev_page = ttk.Button(
            self.pagination_frame,
            text="< Prev",
            command=self.prev_page,
            state="disabled",
        )
        self.btn_prev_page.pack(side=tk.LEFT, padx=5)

        self.lbl_page_info = ttk.Label(
            self.pagination_frame, text="Page 1 of 1"
        )
        self.lbl_page_info.pack(side=tk.LEFT, padx=5)

        self.btn_next_page = ttk.Button(
            self.pagination_frame,
            text="Next >",
            command=self.next_page,
            state="disabled",
        )
        self.btn_next_page.pack(side=tk.LEFT, padx=5)

        # Treeview
        columns = ("id", "flight_no", "date", "vehicle", "mission", "note")
        self.tree = ttk.Treeview(
            self.history_frame, columns=columns, show="headings"
        )

        self.tree.heading("id", text="ID", command=lambda: self.sort_logs("id"))
        self.tree.column("id", width=0, stretch=False)

        self.tree.heading(
            "flight_no",
            text="Flight ID",
            command=lambda: self.sort_logs("flight_no"),
        )
        # self.tree.heading(
        #     "date", text="Date", command=lambda: self.sort_logs("date")
        # )
        self.tree.heading(
            "vehicle",
            text="Vehicle",
            command=lambda: self.sort_logs("vehicle_name"),
        )

        self.tree.heading(
            "mission",
            text="Mission Title",
            command=lambda: self.sort_logs("mission_title"),
        )
        self.tree.heading(
            "note", text="Note", command=lambda: self.sort_logs("note")
        )

        self.tree.column("flight_no", width=60)
        self.tree.column("date", width=0, stretch=False)
        self.tree.column("vehicle", width=100)
        self.tree.column("mission", width=150)
        self.tree.column("note", width=300)

        scrollbar_v = ttk.Scrollbar(
            self.history_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        scrollbar_h = ttk.Scrollbar(
            self.history_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )

        self.tree.configure(yscroll=scrollbar_v.set, xscroll=scrollbar_h.set)

        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", self.on_history_double_click)

        self.load_logs()
        self.refresh_vehicle_ui()

    def reset_filter(self):
        """Resets the filter criteria to defaults."""
        self.filter_id.set("")
        self.filter_date.set(datetime.date.today().strftime("%Y-%m-%d"))
        self.filter_vehicle.set("All")
        self.load_logs()

    def sort_logs(self, col: str):
        """Sorts the logs by the specified column.

        Args:
            col: The column name to sort by.
        """
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True
        self.load_logs()

    def browse_param_file(self):
        """Opens a file dialog to select a parameter file."""
        filename = filedialog.askopenfilename(title="Select Parameter File")
        if filename:
            self.entry_param_file.state(["!readonly"])
            self.entry_param_file.delete(0, tk.END)
            self.entry_param_file.insert(0, filename)
            self.entry_param_file.state(["readonly"])

    def browse_log_file(self):
        """Opens a file dialog to select a flight log file."""
        filename = filedialog.askopenfilename(title="Select Flight Log File")
        if filename:
            self.entry_log_file.state(["!readonly"])
            self.entry_log_file.delete(0, tk.END)
            self.entry_log_file.insert(0, filename)
            self.entry_log_file.state(["readonly"])

    def compare_params_from_input(self):
        """Initiates parameter comparison using the selected file."""
        param_file = self.entry_param_file.get().strip()
        current_content = ""
        if param_file:
            try:
                with open(param_file, "r") as f:
                    current_content = f.read()
            except Exception as e:
                messagebox.showerror("Error", f"Read file failed: {e}")
                return
        else:
            messagebox.showwarning("Warning", "No file selected to compare.")
            return

        vehicle = self.combo_vehicle.get()
        if not vehicle:
            messagebox.showwarning("Warning", "Please select a vehicle first.")
            return

        ComparisonDialog(self.root, self.db, vehicle, current_content)

    def on_history_double_click(self, event: tk.Event):
        """Handles double-click events on the history treeview."""
        item_id = self.tree.selection()
        if not item_id:
            return

        vals = self.tree.item(item_id, "values")
        log_id = int(vals[0])

        FlightDetailsDialog(self.root, self.db, log_id)

    def open_ignore_settings(self):
        """Opens the Ignore Settings dialog."""
        IgnoreSettingsDialog(self.root, self.db)

    def open_vehicle_settings(self):
        """Opens the Vehicle Settings dialog."""
        VehicleSettingsDialog(
            self.root, self.db, on_close_callback=self.refresh_vehicle_ui
        )

    def open_checklist_settings(self):
        """Opens the Checklist Settings dialog."""
        ChecklistSettingsDialog(
            self.root, self.db, on_close_callback=self.refresh_checklist_ui
        )

    def refresh_checklist_ui(self):
        """Refreshes the dynamic checklist UI based on database config."""
        for widget in self.checklist_frame.winfo_children():
            widget.destroy()
        self.dynamic_widgets = {}

        for name, itype, options, _, _ in self.db.get_checklist_items():
            frame = ttk.Frame(self.checklist_frame)
            frame.pack(fill=tk.X, pady=2, padx=5)

            if itype == "text":
                ttk.Label(frame, text=f"{name}:", width=20).pack(side=tk.LEFT)
                entry = ttk.Entry(frame)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.dynamic_widgets[name] = {"type": "text", "var": entry}
            elif itype == "single_select":
                ttk.Label(frame, text=f"{name}:", width=20).pack(side=tk.LEFT)
                vals = (
                    [opt.strip() for opt in options.split(",")]
                    if options
                    else []
                )
                combo = ttk.Combobox(frame, values=vals, state="readonly")
                combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.dynamic_widgets[name] = {
                    "type": "single_select",
                    "var": combo,
                }
            else:
                var = tk.BooleanVar()
                chk = ttk.Checkbutton(frame, text=name, variable=var)
                chk.pack(side=tk.LEFT)
                self.dynamic_widgets[name] = {"type": "checkbox", "var": var}

    def refresh_vehicle_ui(self):
        """Refreshes the vehicle comboboxes."""
        vehicles = self.db.get_vehicles(include_archived=False)
        self.combo_vehicle["values"] = vehicles

        current = self.combo_vehicle.get()
        if vehicles:
            if current not in vehicles:
                self.combo_vehicle.current(0)
        else:
            self.combo_vehicle.set("")

        # Update Filter Vehicle List: Union of 'vehicles' table and 'logs'
        # This ensures we see:
        # 1. Newly added vehicles (even if no logs yet)
        # 2. Archived/Deleted vehicles that have logs
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT name FROM vehicles
            UNION
            SELECT DISTINCT vehicle_name FROM logs
            ORDER BY name
            """
        )
        hist_vehicles = ["All"] + [r[0] for r in cursor.fetchall()]
        self.combo_filter_vehicle["values"] = hist_vehicles

    def calculate_next_id(self):
        """Calculates and sets the next flight ID based on the selected date."""
        date_val = self.log_date_var.get().strip()
        if not date_val:
            return

        next_id = self.db.get_next_flight_id(date_val)
        self.entry_flight_no.delete(0, tk.END)
        self.entry_flight_no.insert(0, str(next_id))

    def save_log(self):
        """Validates and initiates the log saving process in a separate thread."""
        flight_no = self.entry_flight_no.get().strip()
        date = self.log_date_var.get().strip()
        vehicle = self.combo_vehicle.get().strip()
        mission = self.entry_mission_title.get().strip()
        note = self.text_note.get("1.0", tk.END).strip()

        # Validations
        if not flight_no:
            messagebox.showwarning("Validation Error", "Flight ID is required!")
            return
        if not vehicle:
            messagebox.showwarning(
                "Validation Error", "Vehicle selection is required!"
            )
            return

        # Prepare Param Content
        param_file = self.entry_param_file.get().strip()
        param_content = ""
        if param_file:
            try:
                with open(param_file, "r") as f:
                    param_content = f.read()
            except Exception as e:
                messagebox.showerror(
                    "File Error", f"Could not read parameter file:\n{e}"
                )
                return

        # Prepare Checklist JSON
        checklist_data = []
        for name, data in self.dynamic_widgets.items():
            item_type = data["type"]
            val = None
            if item_type == "checkbox":
                val = data["var"].get()  # Boolean
            else:
                val = data["var"].get().strip()  # String

            checklist_data.append(
                {"name": name, "type": item_type, "value": val}
            )
        system_check_json = json.dumps(checklist_data)

        # Data Packet
        log_data = {
            "flight_no": flight_no,
            "date": date,
            "vehicle_name": vehicle,
            "mission_title": mission,
            "note": note,
            "system_check": system_check_json,
            "parameter_changes": param_content,
            "log_file_path": None,  # To be filled in thread
        }

        # Log File Info
        log_source = self.entry_log_file.get().strip()

        # Disable UI during save
        self.root.config(cursor="watch")

        # Start Thread
        threading.Thread(
            target=self._save_log_thread,
            args=(log_data, log_source),
            daemon=True,
        ).start()

    def _save_log_thread(
        self, log_data: Dict[str, Any], log_source: Optional[str]
    ):
        """Threaded function to handle file copying and database insertion."""
        try:
            saved_log_path = None
            if log_source:
                # Use the decoupled file manager
                saved_log_path = self.file_manager.save_log_file(
                    log_source,
                    log_data["date"],
                    log_data["vehicle_name"],
                    log_data["flight_no"],
                )

            log_data["log_file_path"] = saved_log_path

            # Insert to DB (Thread-safe due to check_same_thread=False)
            self.db.insert_log(log_data)

            # Success Callback
            self.root.after(0, self._on_save_success)

        except Exception as e:
            # Error Callback
            self.root.after(0, lambda: self._on_save_error(str(e)))

    def _on_save_success(self):
        """Callback for successful save."""
        self.root.config(cursor="")
        messagebox.showinfo("Success", "Log saved successfully!")
        self.clear_form()
        self.load_logs(reset_page=True)
        self.refresh_vehicle_ui()

    def _on_save_error(self, error_msg: str):
        """Callback for failed save."""
        self.root.config(cursor="")
        messagebox.showerror(
            "Save Error", f"An error occurred during save:\n{error_msg}"
        )

    def load_logs_debounced(self, *args):
        """Debounced wrapper for load_logs."""
        if self._debounce_timer:
            self.root.after_cancel(self._debounce_timer)
        self._debounce_timer = self.root.after(
            300, lambda: self.load_logs(reset_page=True)
        )

    def prev_page(self):
        """Navigates to the previous page of logs."""
        if self.page > 0:
            self.page -= 1
            self.load_logs(reset_page=False)

    def next_page(self):
        """Navigates to the next page of logs."""
        self.page += 1
        self.load_logs(reset_page=False)

    def load_logs(self, reset_page: bool = False):
        """Loads flight logs from the database into the treeview.

        Args:
            reset_page: Whether to reset pagination to the first page.
        """
        if reset_page:
            self.page = 0

        filter_id = self.filter_id.get().strip()
        filter_date = self.filter_date.get().strip()
        filter_vehicle = self.filter_vehicle.get()

        # Get count for pagination
        total_count = self.db.get_logs_count(
            filter_id, filter_date, filter_vehicle
        )
        total_pages = (
            math.ceil(total_count / self.page_size) if total_count > 0 else 1
        )

        if self.page >= total_pages:
            self.page = total_pages - 1
        if self.page < 0:
            self.page = 0

        offset = self.page * self.page_size

        rows = self.db.get_logs(
            filter_id,
            filter_date,
            filter_vehicle,
            self.sort_col,
            self.sort_desc,
            self.page_size,
            offset,
        )

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            d = list(row)
            # Row structure from get_logs:
            # id(0), flight_no(1), date(2), vehicle_name(3), system_check(4),
            # mission(5), param(6), log_path(7), note(8)

            # Display: id, flight_no, date, vehicle, mission, note
            display_data = [d[0], d[1], d[2], d[3], d[5], d[8]]

            # Sanitize Note for display
            if display_data[5]:
                display_data[5] = display_data[5].replace("\n", " ")
            else:
                display_data[5] = ""

            if not display_data[4]:
                display_data[4] = ""

            self.tree.insert("", tk.END, values=display_data)

        # Update Pagination UI
        self.lbl_page_info.config(
            text=f"Page {self.page + 1} of {total_pages} (Total: {total_count})"
        )

        self.btn_prev_page.state(
            ["!disabled"] if self.page > 0 else ["disabled"]
        )
        self.btn_next_page.state(
            ["!disabled"] if self.page < total_pages - 1 else ["disabled"]
        )

    def clear_form(self):
        """Clears all input fields in the log entry form."""
        self.entry_mission_title.delete(0, tk.END)
        self.text_note.delete("1.0", tk.END)
        self.log_date_var.set(datetime.date.today().strftime("%Y-%m-%d"))

        for data in self.dynamic_widgets.values():
            if data["type"] == "checkbox":
                data["var"].set(False)
            elif data["type"] == "text":
                data["var"].delete(0, tk.END)
            elif data["type"] == "single_select":
                data["var"].set("")

        # Reset Files
        self.entry_param_file.state(["!readonly"])
        self.entry_param_file.delete(0, tk.END)
        self.entry_param_file.state(["readonly"])

        self.entry_log_file.state(["!readonly"])
        self.entry_log_file.delete(0, tk.END)
        self.entry_log_file.state(["readonly"])

        self.calculate_next_id()
