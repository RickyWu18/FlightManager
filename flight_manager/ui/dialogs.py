"""Dialog windows for the Flight Manager application.

This module contains various dialog classes for settings management,
parameter comparison, and viewing flight details.
"""

import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Callable, Optional

from flight_manager.utils import compare_params


class BaseSettingsDialog(tk.Toplevel):
    """Base class for settings dialogs."""

    def __init__(
        self, parent: tk.Widget, title: str, geometry: str = "400x400"
    ):
        """Initializes the BaseSettingsDialog.

        Args:
            parent: The parent widget.
            title: The title of the dialog.
            geometry: The size of the dialog (e.g., "400x400").
        """
        super().__init__(parent)
        self.title(title)

        # Center the window relative to parent
        try:
            width, height = map(int, geometry.split("x"))
            parent.update_idletasks()
            x = (
                parent.winfo_rootx()
                + (parent.winfo_width() // 2)
                - (width // 2)
            )
            y = (
                parent.winfo_rooty()
                + (parent.winfo_height() // 2)
                - (height // 2)
            )
            self.geometry(f"{geometry}+{x}+{y}")
        except ValueError:
            # Fallback if geometry string is complex or invalid
            self.geometry(geometry)

        self.transient(parent)
        self.grab_set()

    def _create_scrolled_list(self, parent, list_height=10):
        """Creates a Frame containing a Listbox, Scrollbar, and Sidebar Button Frame."""
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        lb = tk.Listbox(container, height=list_height, font=("Segoe UI", 11))
        sb = ttk.Scrollbar(container, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)

        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)

        btn_frame = ttk.Frame(container, padding=(10, 0))
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        return lb, btn_frame

    def _create_scrolled_tree(self, parent, columns, headings):
        """Creates a Frame containing a Treeview, Scrollbar, and Sidebar Button Frame."""
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        for col, head in zip(columns, headings):
            tree.heading(col, text=head)

        sb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscroll=sb.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(container, padding=(10, 0))
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        return tree, btn_frame


class PreferencesDialog(BaseSettingsDialog):
    """Dialog for managing application preferences (Performance/UI)."""

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: Any,
        on_save_callback: Optional[Callable[[int], None]] = None,
    ):
        """Initializes the PreferencesDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            on_save_callback: Optional callback when settings are saved.
        """
        super().__init__(parent, "Performance & UI Settings", "400x500")
        self.db = db_manager
        self.on_save_callback = on_save_callback

        content_frame = ttk.Frame(self, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Font Size
        ttk.Label(content_frame, text="Global Font Size:", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 5))

        current_size = int(self.db.get_setting("font_size", 10))
        self.size_var = tk.IntVar(value=current_size)
        self.spin = ttk.Spinbox(content_frame, from_=8, to_=24, textvariable=self.size_var, width=10, font=("Segoe UI", 11))
        self.spin.pack(anchor="w", pady=(0, 10))

        ttk.Separator(content_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Feature Permissions
        ttk.Label(content_frame, text="Feature Permissions:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self.vars = {}
        features = [
            ("enable_edit_log", "Enable Edit Log Info"),
            ("enable_delete_log", "Enable Delete Log"),
            ("enable_update_params", "Enable Update Parameters"),
            ("enable_update_log_file", "Enable Update Log File"),
        ]

        for key, label in features:
            var = tk.BooleanVar(value=self.db.get_setting(key, "1") == "1")
            chk = ttk.Checkbutton(content_frame, text=label, variable=var)
            chk.pack(anchor="w", pady=2)
            self.vars[key] = var

        ttk.Separator(content_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Log Storage Management
        ttk.Label(content_frame, text="Log Storage Management:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        # Max Size
        ttk.Label(content_frame, text="Max Log Folder Size (GB, 0=Unlimited):").pack(anchor="w")
        current_max_size = float(self.db.get_setting("log_max_size_gb", "0"))
        self.max_size_var = tk.DoubleVar(value=current_max_size)
        self.spin_max_size = ttk.Spinbox(content_frame, from_=0, to_=9999, increment=0.1, textvariable=self.max_size_var, width=10)
        self.spin_max_size.pack(anchor="w", pady=(0, 5))

        # Retention
        ttk.Label(content_frame, text="Retention Period (Days, 0=Unlimited):").pack(anchor="w")
        current_retention = int(self.db.get_setting("log_retention_days", "0"))
        self.retention_var = tk.IntVar(value=current_retention)
        self.spin_retention = ttk.Spinbox(content_frame, from_=0, to_=9999, textvariable=self.retention_var, width=10)
        self.spin_retention.pack(anchor="w", pady=(0, 5))

        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X, pady=20)

        ttk.Button(btn_frame, text="Save", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Apply", command=self.apply_settings).pack(side=tk.LEFT, padx=5)

        ttk.Label(content_frame, text="Note: Some changes may require app restart for full effect.", font=("Segoe UI", 8), foreground="gray").pack(pady=10)

    def apply_settings(self):
        """Applies the current settings via callback without saving to DB."""
        new_size = self.size_var.get()
        if self.on_save_callback:
            self.on_save_callback(new_size)

    def save_settings(self):
        """Saves the settings to the database and triggers callback."""
        new_size = self.size_var.get()
        self.db.set_setting("font_size", new_size)

        for key, var in self.vars.items():
            self.db.set_setting(key, "1" if var.get() else "0")

        # Save Storage Settings
        self.db.set_setting("log_max_size_gb", str(self.max_size_var.get()))
        self.db.set_setting("log_retention_days", str(self.retention_var.get()))

        if self.on_save_callback:
            self.on_save_callback(new_size)

        messagebox.showinfo("Success", "Settings saved successfully.")
        self.destroy()


class IgnoreSettingsDialog(BaseSettingsDialog):
    """Dialog for managing ignore patterns."""

    def __init__(self, parent: tk.Widget, db_manager: Any):
        """Initializes the IgnoreSettingsDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
        """
        super().__init__(parent, "Manage Ignore Patterns", "500x450")
        self.db = db_manager

        content_frame = ttk.Frame(self, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content_frame, text="Patterns (Unix Wildcards e.g., *STAT*, PID_*)"
        ).pack(anchor="w", pady=(0, 5))

        # --- Top Section: List + Right Actions ---
        self.lb, side_btn_frame = self._create_scrolled_list(content_frame)

        ttk.Button( side_btn_frame, text="Delete", command=self.delete_item).pack(
            fill=tk.X, pady=2
        )

        self.load_list()

        # --- Bottom Section: Add New ---
        add_frame = ttk.LabelFrame(
            content_frame, text="Add New Pattern", padding=15
        )
        add_frame.pack(fill=tk.X)

        add_frame.columnconfigure(0, weight=1)
        self.entry_new = ttk.Entry(add_frame, font=("Segoe UI", 11))
        self.entry_new.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=3)

        ttk.Button(
            add_frame, text="Add Pattern", command=self.add_item, width=15
        ).grid(row=0, column=1, sticky="e", ipady=1)

    def load_list(self):
        """Loads ignore patterns from the database into the listbox."""
        self.lb.delete(0, tk.END)
        for pattern in self.db.get_ignore_patterns():
            self.lb.insert(tk.END, pattern)

    def add_item(self):
        """Adds a new ignore pattern."""
        val = self.entry_new.get().strip()
        if val:
            if self.db.add_ignore_pattern(val):
                self.entry_new.delete(0, tk.END)
                self.load_list()
            else:
                messagebox.showerror("Error", "Pattern already exists!")

    def delete_item(self):
        """Deletes the selected ignore pattern."""
        sel = self.lb.curselection()
        if sel:
            val = self.lb.get(sel[0])
            if messagebox.askyesno("Confirm", f"Delete '{val}'?"):
                self.db.delete_ignore_pattern(val)
                self.load_list()


class VehicleSettingsDialog(BaseSettingsDialog):
    """Dialog for managing vehicles."""

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: Any,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        """Initializes the VehicleSettingsDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            on_close_callback: Optional callback when dialog closes.
        """
        super().__init__(parent, "Manage Vehicles", "500x400")
        self.db = db_manager
        self.on_close_callback = on_close_callback

        content_frame = ttk.Frame(self, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Section: List + Right Actions ---
        ttk.Label(content_frame, text="Current Vehicles:").pack(
            anchor="w", pady=(0, 5)
        )

        self.lb, side_btn_frame = self._create_scrolled_list(content_frame)

        ttk.Button(
            side_btn_frame,
            text="Toggle Archive",
            command=self.toggle_archive,
            width=15,
        ).pack(fill=tk.X, pady=2)

        self.load_list()

        # --- Bottom Section: Add New (Moved back to bottom and kept taller) ---
        add_frame = ttk.LabelFrame(
            content_frame, text="Add New Vehicle", padding=15
        )
        add_frame.pack(fill=tk.X)

        add_frame.columnconfigure(0, weight=1)
        self.entry_new = ttk.Entry(add_frame, font=("Segoe UI", 11))
        self.entry_new.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=3)

        ttk.Button(
            add_frame, text="Add Vehicle", command=self.add_item, width=15
        ).grid(row=0, column=1, sticky="e", ipady=1)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_list(self):
        """Loads vehicles from the database into the listbox."""
        self.lb.delete(0, tk.END)
        for name, archived in self.db.get_vehicles(include_archived=True):
            display = name + (" [ARCHIVED]" if archived else "")
            self.lb.insert(tk.END, display)
            # Optional: color code archived items if desired, but standard Listbox
            # item config is a bit verbose. Keeping simple text for now.

    def add_item(self):
        """Adds a new vehicle."""
        val = self.entry_new.get().strip()
        if val:
            if self.db.add_vehicle(val):
                self.entry_new.delete(0, tk.END)
                self.load_list()
            else:
                messagebox.showerror("Error", "Vehicle already exists!")

    def toggle_archive(self):
        """Toggles the archive status of the selected vehicle."""
        sel = self.lb.curselection()
        if sel:
            full_str = self.lb.get(sel[0])
            name = full_str.split(" [ARCHIVED]")[0]
            self.db.toggle_vehicle_archive(name)
            self.load_list()

    def on_close(self):
        """Handles the dialog close event."""
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


class ChecklistSettingsDialog(BaseSettingsDialog):
    """Dialog for managing checklist items."""

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: Any,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        """Initializes the ChecklistSettingsDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            on_close_callback: Optional callback when dialog closes.
        """
        super().__init__(parent, "Manage Preflight Checklist", "700x500")
        self.db = db_manager
        self.on_close_callback = on_close_callback

        # Main Layout
        content_frame = ttk.Frame(self, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Top Section: Treeview + Side Buttons
        columns = ("name", "type", "options", "rule")
        headings = ("Name", "Type", "Options", "Rule")
        self.tree, btn_frame = self._create_scrolled_tree(content_frame, columns, headings)

        self.tree.column("name", width=200)
        self.tree.column("type", width=100)
        self.tree.column("options", width=100)
        self.tree.column("rule", width=100)

        self.tree.bind("<Double-1>", lambda e: self.edit_item())

        # --- Action Buttons (Right) ---
        ttk.Button(
            btn_frame, text="▲ Move Up", command=lambda: self.move_item(-1)
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            btn_frame, text="▼ Move Down", command=lambda: self.move_item(1)
        ).pack(fill=tk.X, pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_item).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(btn_frame, text="Delete", command=self.delete_item).pack(
            fill=tk.X, pady=2
        )

        # --- Bottom Section: Add New ---
        self.create_add_ui(content_frame)

        self.checklist_map = {}  # Map tree item ID to DB ID and Data
        self.load_list()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_list(self):
        """Loads checklist items from the database into the Treeview."""
        # Clear current items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.checklist_map = {}

        checklist_items = self.db.get_checklist_items()

        for name, itype, opts, rule, pid, _ in checklist_items:
            opts_display = opts if opts else ""
            rule_display = rule if rule else ""
            item_id = self.tree.insert(
                "", tk.END, values=(name, itype, opts_display, rule_display)
            )
            self.checklist_map[item_id] = {
                "id": pid,
                "name": name,
                "type": itype,
                "options": opts,
                "rule": rule,
            }

    def create_add_ui(self, parent):
        """Creates the UI for adding new checklist items."""
        ctrl_frame = ttk.LabelFrame(parent, text="Add New Item", padding=10)
        ctrl_frame.pack(fill=tk.X)

        grid_frame = ttk.Frame(ctrl_frame)
        grid_frame.pack(fill=tk.X)

        ttk.Label(grid_frame, text="Name:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.entry_new = ttk.Entry(grid_frame)
        self.entry_new.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(grid_frame, text="Type:").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.type_var = tk.StringVar(value="checkbox")
        type_combo = ttk.Combobox(
            grid_frame,
            textvariable=self.type_var,
            values=["checkbox", "text", "single_select"],
            state="readonly",
        )
        type_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.lbl_opts = ttk.Label(grid_frame, text="Options (comma sep):")
        self.entry_opts = ttk.Entry(grid_frame)

        ttk.Label(grid_frame, text="Rule (eg. value > 10, value == true):").grid(
            row=3, column=0, sticky="w", pady=2
        )
        self.entry_rule = ttk.Entry(grid_frame)
        self.entry_rule.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

        type_combo.bind("<<ComboboxSelected>>", self.toggle_options)
        self.toggle_options()

        grid_frame.columnconfigure(1, weight=1)

        ttk.Button(ctrl_frame, text="Add Item", command=self.add_item).pack(
            pady=(10, 0), anchor="e"
        )

    def toggle_options(self, event=None):
        """Toggles the visibility of the options entry."""
        if self.type_var.get() == "single_select":
            self.lbl_opts.grid(row=2, column=0, sticky="w", pady=2)
            self.entry_opts.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        else:
            self.lbl_opts.grid_forget()
            self.entry_opts.grid_forget()

    def add_item(self):
        """Adds a new checklist item."""
        val = self.entry_new.get().strip()
        itype = self.type_var.get()
        opts = (
            self.entry_opts.get().strip() if itype == "single_select" else None
        )
        rule = self.entry_rule.get().strip() or None

        if val:
            if self.db.add_checklist_item(val, itype, opts, rule):
                self.entry_new.delete(0, tk.END)
                self.entry_opts.delete(0, tk.END)
                self.entry_rule.delete(0, tk.END)
                self.load_list()
                # Scroll to bottom
                if self.tree.get_children():
                    self.tree.see(self.tree.get_children()[-1])
            else:
                messagebox.showerror("Error", "Item already exists!")

    def get_selected_id(self) -> Optional[str]:
        """Returns the Treeview Item ID of the selected row."""
        sel = self.tree.selection()
        return sel[0] if sel else None

    def move_item(self, direction: int):
        """Moves the selected item up or down."""
        sel_item_id = self.get_selected_id()
        if not sel_item_id:
            return

        idx = self.tree.index(sel_item_id)
        children = self.tree.get_children()

        if direction == -1 and idx > 0:
            swap_item_id = children[idx - 1]
        elif direction == 1 and idx < len(children) - 1:
            swap_item_id = children[idx + 1]
        else:
            return

        db_id1 = self.checklist_map[sel_item_id]["id"]
        db_id2 = self.checklist_map[swap_item_id]["id"]

        self.db.swap_checklist_order(db_id1, db_id2)
        self.load_list()

        # Restore selection using the DB ID logic (find the new tree item that has the same DB ID)
        for item in self.tree.get_children():
            if self.checklist_map[item]["id"] == db_id1:
                self.tree.selection_set(item)
                self.tree.see(item)
                break

    def delete_item(self):
        """Deletes the selected checklist item."""
        sel_item_id = self.get_selected_id()
        if not sel_item_id:
            return

        data = self.checklist_map[sel_item_id]
        if messagebox.askyesno("Confirm", f"Delete '{data['name']}'?"):
            self.db.delete_checklist_item(data["id"])
            self.load_list()

    def edit_item(self):
        """Opens a dialog to edit the selected item."""
        sel_item_id = self.get_selected_id()
        if not sel_item_id:
            return

        data = self.checklist_map[sel_item_id]

        # Create a simple modal dialog
        dlg = tk.Toplevel(self)
        dlg.title("Edit Item")
        dlg.geometry("400x350")
        dlg.transient(self)
        dlg.grab_set()
        dlg.focus_set()

        # Center dialog
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 175
        dlg.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dlg, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Name:").pack(anchor="w")
        entry_name = ttk.Entry(main_frame)
        entry_name.pack(fill=tk.X, pady=(5, 10))
        entry_name.insert(0, data["name"])
        entry_name.focus_set()

        ttk.Label(main_frame, text="Type:").pack(anchor="w")
        type_var = tk.StringVar(value=data["type"])
        combo_type = ttk.Combobox(
            main_frame,
            textvariable=type_var,
            values=["checkbox", "text", "single_select"],
            state="readonly",
        )
        combo_type.pack(fill=tk.X, pady=(5, 10))

        # Container for options to keep order fixed
        opts_container = ttk.Frame(main_frame)
        opts_container.pack(fill=tk.X)

        lbl_opts = ttk.Label(opts_container, text="Options (comma sep):")
        entry_opts = ttk.Entry(opts_container)

        def update_opts_visibility(event=None):
            if type_var.get() == "single_select":
                lbl_opts.pack(anchor="w")
                entry_opts.pack(fill=tk.X, pady=(5, 10))
            else:
                lbl_opts.pack_forget()
                entry_opts.pack_forget()

        combo_type.bind("<<ComboboxSelected>>", update_opts_visibility)

        if data["options"]:
            entry_opts.insert(0, data["options"])

        update_opts_visibility()

        ttk.Label(main_frame, text="Rule (eg. value > 10, value == true):").pack(anchor="w")
        entry_rule = ttk.Entry(main_frame)
        entry_rule.pack(fill=tk.X, pady=(5, 10))
        if data.get("rule"):
            entry_rule.insert(0, data["rule"])

        def save_edit():
            new_name = entry_name.get().strip()
            new_type = type_var.get()
            new_opts = (
                entry_opts.get().strip()
                if new_type == "single_select"
                else None
            )
            new_rule = entry_rule.get().strip() or None

            if not new_name:
                messagebox.showwarning(
                    "Warning", "Name cannot be empty.", parent=dlg
                )
                return

            try:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    "UPDATE checklist_config SET item_name=?, item_type=?, options=?, validation_rule=? WHERE id=?",
                    (new_name, new_type, new_opts, new_rule, data["id"]),
                )
                self.db.conn.commit()
                dlg.destroy()
                self.load_list()

                # Reselect
                for item in self.tree.get_children():
                    if self.checklist_map[item]["id"] == data["id"]:
                        self.tree.selection_set(item)
                        break

            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}", parent=dlg)

        ttk.Button(main_frame, text="Save Changes", command=save_edit).pack(
            pady=10
        )

    def on_close(self):
        """Handles the dialog close event."""
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


class LogEditDialog(BaseSettingsDialog):
    """Dialog for editing an existing flight log."""

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: Any,
        log_id: int,
        on_save_callback: Optional[Callable[[], None]] = None,
    ):
        """Initializes the LogEditDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            log_id: The ID of the log to edit.
            on_save_callback: Optional callback when log is saved.
        """
        super().__init__(parent, "Edit Flight Log", "600x800")
        self.db = db_manager
        self.log_id = log_id
        self.on_save_callback = on_save_callback

        row = self.db.get_log_by_id(log_id)
        if not row:
            self.destroy()
            return

        (
            self.flight_no,
            self.date,
            self.vehicle,
            checks_json,
            self.param_content,
            self.log_path,
            self.mission,
            self.note,
        ) = row

        self.dynamic_widgets = {}
        self.create_widgets(checks_json)

    def create_widgets(self, checks_json: str):
        """Creates the widgets for the dialog."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Basic Info
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text="Date:").grid(row=0, column=0, sticky="w")
        self.entry_date = ttk.Entry(info_frame)
        self.entry_date.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.entry_date.insert(0, self.date)

        ttk.Label(info_frame, text="Vehicle:").grid(row=1, column=0, sticky="w")
        vehicles = self.db.get_vehicles(include_archived=True)
        vehicle_names = [v if isinstance(v, str) else v[0] for v in vehicles]
        if self.vehicle not in vehicle_names:
            vehicle_names.append(self.vehicle)

        self.combo_vehicle = ttk.Combobox(
            info_frame, values=vehicle_names, state="readonly"
        )
        self.combo_vehicle.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.combo_vehicle.set(self.vehicle)

        ttk.Label(info_frame, text="Flight ID:").grid(
            row=2, column=0, sticky="w"
        )
        self.entry_flight_no = ttk.Entry(info_frame)
        self.entry_flight_no.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.entry_flight_no.insert(0, self.flight_no)

        ttk.Label(info_frame, text="Mission:").grid(row=3, column=0, sticky="w")
        self.entry_mission = ttk.Entry(info_frame)
        self.entry_mission.grid(
            row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=2
        )
        self.entry_mission.insert(0, self.mission if self.mission else "")

        info_frame.columnconfigure(1, weight=1)

        # Checklist
        check_frame = ttk.LabelFrame(
            main_frame, text="Preflight Check", padding=10
        )
        check_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        canvas = tk.Canvas(check_frame, height=200)
        scrollbar = ttk.Scrollbar(
            check_frame, orient="vertical", command=canvas.yview
        )
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checklist_data = []
        try:
            checklist_data = json.loads(checks_json)
        except Exception:
            pass

        for item in checklist_data:
            f = ttk.Frame(scroll_frame)
            f.pack(fill=tk.X, pady=2, padx=5)

            name = item.get("name", "??")
            itype = item.get("type", "checkbox")
            val = item.get("value", "")

            if itype == "text":
                ttk.Label(f, text=f"{name}:", width=25).pack(side=tk.LEFT)
                e = ttk.Entry(f)
                e.insert(0, str(val))
                e.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.dynamic_widgets[name] = {"type": "text", "var": e}
            elif itype == "single_select":
                ttk.Label(f, text=f"{name}:", width=25).pack(side=tk.LEFT)
                e = ttk.Entry(f)
                e.insert(0, str(val))
                e.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.dynamic_widgets[name] = {
                    "type": "single_select",
                    "var": e,
                }
            else:
                is_checked = val is True or str(val).lower() == "true"
                var = tk.BooleanVar(value=is_checked)
                chk = ttk.Checkbutton(f, text=name, variable=var)
                chk.pack(side=tk.LEFT)
                self.dynamic_widgets[name] = {"type": "checkbox", "var": var}

        # Note
        note_frame = ttk.LabelFrame(main_frame, text="Note", padding=10)
        note_frame.pack(fill=tk.X, pady=5)

        font_size = int(self.db.get_setting("font_size", 10))
        self.text_note = scrolledtext.ScrolledText(
            note_frame, height=5, font=("Segoe UI", font_size)
        )
        self.text_note.insert(tk.END, self.note if self.note else "")
        self.text_note.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Save Changes", command=self.save_log).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def save_log(self):
        """Saves the edited log back to the database."""
        flight_no = self.entry_flight_no.get().strip()
        date = self.entry_date.get().strip()
        vehicle = self.combo_vehicle.get().strip()
        mission = self.entry_mission.get().strip()
        note = self.text_note.get("1.0", tk.END).strip()

        if not flight_no or not date or not vehicle:
            messagebox.showwarning(
                "Warning", "Flight ID, Date, and Vehicle are required."
            )
            return

        # Prepare Checklist JSON
        checklist_data = []
        for name, data in self.dynamic_widgets.items():
            item_type = data["type"]
            val = None
            if item_type == "checkbox":
                val = data["var"].get()
            else:
                val = data["var"].get().strip()
            checklist_data.append(
                {"name": name, "type": item_type, "value": val}
            )

        system_check_json = json.dumps(checklist_data)

        log_data = {
            "flight_no": flight_no,
            "date": date,
            "vehicle_name": vehicle,
            "mission_title": mission,
            "note": note,
            "system_check": system_check_json,
            "parameter_changes": self.param_content,
            "log_file_path": self.log_path,
        }

        try:
            self.db.update_log(self.log_id, log_data)
            messagebox.showinfo("Success", "Log updated successfully.")
            if self.on_save_callback:
                self.on_save_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update log: {e}")


    def on_close(self):
        """Handles the dialog close event."""
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


class ComparisonDialog(tk.Toplevel):
    """Dialog for comparing parameter sets."""

    def __init__(
        self,
        parent: tk.Widget,
        db_manager: Any,
        vehicle: str,
        current_content: str,
        exclude_id: Optional[int] = None,
    ):
        """Initializes the ComparisonDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            vehicle: The name of the vehicle.
            current_content: The current parameter content.
            exclude_id: ID to exclude from history (typically current flight).
        """
        super().__init__(parent)
        self.db = db_manager
        self.vehicle = vehicle
        self.current_content = current_content
        self.exclude_id = exclude_id

        self.title("Parameter Comparison")
        self.geometry("800x600")

        self.create_widgets()
        self.load_history()

    def create_widgets(self):
        """Creates the widgets for the dialog."""
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill=tk.X)
        ttk.Label(top_frame, text="Compare vs:").pack(side=tk.LEFT)

        self.combo = ttk.Combobox(top_frame, state="readonly", width=50)
        self.combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.combo.bind("<<ComboboxSelected>>", self.update_view)

        font_size = int(self.db.get_setting("font_size", 10))
        self.st = scrolledtext.ScrolledText(self, font=("Consolas", font_size))
        self.st.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.st.tag_config("add", foreground="green")
        self.st.tag_config("rem", foreground="red")
        self.st.tag_config("chg", foreground="darkorange")
        self.st.tag_config("head", font=("Consolas", font_size, "bold"))

    def load_history(self):
        """Loads parameter history for the vehicle."""
        rows = self.db.get_log_history_for_vehicle(self.vehicle)
        valid_rows = [r for r in rows if r[0] != self.exclude_id]

        self.history_map = {
            f"{r[0]} | Flight {r[2]} ({r[1]})": r for r in valid_rows
        }
        self.combo["values"] = list(self.history_map.keys())

        if self.combo["values"]:
            # Auto select previous
            default_index = 0
            if self.exclude_id is not None:
                for i, row in enumerate(valid_rows):
                    if row[0] < self.exclude_id:
                        default_index = i
                        break
            self.combo.current(default_index)
            self.update_view()
        else:
            self.st.insert(
                tk.END, "No other history logs found for this vehicle."
            )
            self.st.config(state="disabled")

    def update_view(self, event=None):
        """Updates the comparison view based on selection."""
        sel = self.combo.get()
        self.st.config(state="normal")
        self.st.delete("1.0", tk.END)

        if not sel:
            return

        row = self.history_map[sel]
        ref_content = row[3] if row and row[3] else ""

        ignore_patterns = self.db.get_ignore_patterns()
        added, removed, changed = compare_params(
            self.current_content, ref_content, ignore_patterns
        )

        if not added and not removed and not changed:
            self.st.insert(
                tk.END, "No differences found (checked ignore patterns)."
            )

        if changed:
            self.st.insert(tk.END, "--- Changed Parameters ---\n", "head")
            for k, (old, new) in changed.items():
                self.st.insert(tk.END, f"~ {k}: {old} -> {new}\n", "chg")
            self.st.insert(tk.END, "\n")

        if added:
            self.st.insert(tk.END, "--- Added Parameters ---\n", "head")
            for k, v in added.items():
                self.st.insert(tk.END, f"+ {k}: {v}\n", "add")
            self.st.insert(tk.END, "\n")

        if removed:
            self.st.insert(tk.END, "--- Removed Parameters ---\n", "head")
            for k, v in removed.items():
                self.st.insert(tk.END, f"- {k}: {v}\n", "rem")

        self.st.config(state="disabled")


class FlightDetailsDialog(tk.Toplevel):
    """Dialog for viewing flight details."""

    def __init__(self, parent: tk.Widget, db_manager: Any, log_id: int, file_manager: Any = None, on_update_callback: Optional[Callable[[], None]] = None):
        """Initializes the FlightDetailsDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            log_id: The ID of the flight log.
            file_manager: The file manager instance.
            on_update_callback: Optional callback when log is updated or deleted.
        """
        super().__init__(parent)
        self.db = db_manager
        self.file_manager = file_manager
        self.log_id = log_id
        self.on_update_callback = on_update_callback

        row = self.db.get_log_by_id(log_id)
        if not row:
            self.destroy()
            return

        (
            self.flight_no,
            self.date,
            self.vehicle,
            checks_json,
            self.param_content,
            self.log_path,
            self.mission,
            self.note,
            self.is_locked,
        ) = row
        self.title(f"Flight Details - {self.date} (ID: {self.flight_no})")
        self.geometry("600x850")

        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.create_widgets(checks_json)

    def refresh_ui(self):
        """Reloads data from DB and refreshes the UI widgets."""
        row = self.db.get_log_by_id(self.log_id)
        if not row:
            self.destroy()
            return
        (
            self.flight_no,
            self.date,
            self.vehicle,
            checks_json,
            self.param_content,
            self.log_path,
            self.mission,
            self.note,
            self.is_locked,
        ) = row

        for widget in self.container.winfo_children():
            widget.destroy()

        self.create_widgets(checks_json)
        self.title(f"Flight Details - {self.date} (ID: {self.flight_no})")

    def create_widgets(self, checks_json: str):
        """Creates the widgets for the dialog."""
        # Top Action Buttons
        action_frame = ttk.Frame(self.container, padding=10)
        action_frame.pack(fill=tk.X)

        edit_btn = ttk.Button(action_frame, text="Edit Log Info", command=self.edit_log)
        edit_btn.pack(side=tk.LEFT, padx=5)
        if self.db.get_setting("enable_edit_log", "1") == "0" or self.is_locked:
            edit_btn.state(["disabled"])

        del_btn = ttk.Button(action_frame, text="Delete Log", command=self.delete_log)
        del_btn.pack(side=tk.LEFT, padx=5)
        if self.db.get_setting("enable_delete_log", "1") == "0" or self.is_locked:
            del_btn.state(["disabled"])

        lock_text = "🔓 Unlock Log" if self.is_locked else "🔒 Lock Log"
        lock_btn = ttk.Button(action_frame, text=lock_text, command=self.toggle_lock)
        lock_btn.pack(side=tk.LEFT, padx=5)

        info_frame = ttk.LabelFrame(self.container, text="Information", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(info_frame, text=f"Date: {self.date}").grid(
            row=0, column=0, sticky="w", padx=10
        )
        ttk.Label(info_frame, text=f"Vehicle: {self.vehicle}").grid(
            row=0, column=1, sticky="w", padx=10
        )
        ttk.Label(info_frame, text=f"Flight ID: {self.flight_no}").grid(
            row=0, column=2, sticky="w", padx=10
        )
        if self.mission:
            ttk.Label(info_frame, text=f"Mission: {self.mission}").grid(
                row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(5, 0)
            )

        if self.note:
            note_frame = ttk.LabelFrame(self.container, text="Note", padding=10)
            note_frame.pack(fill=tk.X, padx=10, pady=5)

            font_size = int(self.db.get_setting("font_size", 10))
            st = scrolledtext.ScrolledText(
                note_frame, height=3, font=("Segoe UI", font_size)
            )
            st.insert(tk.END, self.note)
            st.config(state="disabled")
            st.pack(fill=tk.BOTH, expand=True)

        check_frame = ttk.LabelFrame(self.container, text="Preflight Check", padding=10)
        check_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(check_frame, height=200)
        scrollbar = ttk.Scrollbar(
            check_frame, orient="vertical", command=canvas.yview
        )
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checklist_data = []
        try:
            checklist_data = json.loads(checks_json)
        except Exception:
            if checks_json:
                for item in checks_json.split(", "):
                    if ":" in item:
                        n, v = item.split(": ", 1)
                        checklist_data.append(
                            {"name": n, "type": "text", "value": v}
                        )
                    else:
                        checklist_data.append(
                            {"name": item, "type": "checkbox", "value": True}
                        )

        for item in checklist_data:
            f = ttk.Frame(scroll_frame)
            f.pack(fill=tk.X, pady=2, padx=5)

            name = item.get("name", "??")
            itype = item.get("type", "checkbox")
            val = item.get("value", "")

            if itype == "text" or itype == "single_select":
                ttk.Label(f, text=f"{name}:", width=25).pack(side=tk.LEFT)
                e = ttk.Entry(f)
                e.insert(0, str(val))
                e.state(["readonly"])
                e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                is_checked = val is True or str(val).lower() == "true"
                var = tk.BooleanVar(value=is_checked)
                chk = ttk.Checkbutton(
                    f, text=name, variable=var, state="disabled"
                )
                chk.pack(side=tk.LEFT)

        param_frame = ttk.LabelFrame(self.container, text="Parameter Data", padding=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            param_frame, text="Compare...", command=self.open_compare
        ).pack(side=tk.LEFT, padx=5)

        is_param_none = not self.param_content or not self.param_content.strip()
        param_btn_text = "Upload Params..." if is_param_none else "Update Params..."
        upd_param_btn = ttk.Button(
            param_frame, text=param_btn_text, command=self.update_params
        )
        upd_param_btn.pack(side=tk.LEFT, padx=5)

        # Enable if setting is on OR if it's a first-time upload
        if (self.db.get_setting("enable_update_params", "1") == "0" or self.is_locked) and not is_param_none:
            upd_param_btn.state(["disabled"])

        ttk.Button(
            param_frame, text="Export Params", command=self.export_params
        ).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(self.container, text="Flight Log File", padding=10)
        log_frame.pack(fill=tk.X, padx=10, pady=5)

        file_exists = self.log_path and os.path.exists(self.log_path)
        display_name = os.path.basename(self.log_path) if self.log_path else "None"

        font_size = int(self.db.get_setting("font_size", 10))
        label_font = ("Segoe UI", font_size)

        if self.log_path and not file_exists:
            display_name += " [REMOVED]"
            label_font = ("Segoe UI", font_size, "overstrike")

        self.lbl_log_file = tk.Label(log_frame, text=f"File: {display_name}", font=label_font)
        self.lbl_log_file.pack(side=tk.LEFT, padx=5)

        if self.log_path and file_exists:
            ttk.Button(
                log_frame, text="Export Log", command=self.export_log
            ).pack(side=tk.RIGHT, padx=5)

        is_none = not self.log_path
        btn_text = "Upload Log File..." if is_none else "Update Log File..."
        upd_log_btn = ttk.Button(
            log_frame, text=btn_text, command=self.update_log_file
        )
        upd_log_btn.pack(side=tk.RIGHT, padx=5)

        # Enable if setting is on OR if it's a first-time upload (is_none)
        if (self.db.get_setting("enable_update_log_file", "1") == "0" or self.is_locked) and not is_none:
            upd_log_btn.state(["disabled"])

    def toggle_lock(self):
        """Toggles the lock status of the log."""
        if self.db.toggle_log_lock(self.log_id):
            self.refresh_ui()
            if self.on_update_callback:
                self.on_update_callback()

    def open_compare(self):
        """Opens the comparison dialog for this flight."""
        ComparisonDialog(
            self,
            self.db,
            self.vehicle,
            self.param_content,
            exclude_id=self.log_id,
        )

    def update_params(self):
        """Updates the parameter content from a new file."""
        filename = filedialog.askopenfilename(title="Select New Parameter File")
        if filename:
            try:
                with open(filename, "r") as f:
                    new_content = f.read()

                # Get current log data to update
                row = self.db.get_log_by_id(self.log_id)
                if not row: return

                log_data = {
                    "flight_no": row[0],
                    "date": row[1],
                    "vehicle_name": row[2],
                    "system_check": row[3],
                    "parameter_changes": new_content,
                    "log_file_path": row[5],
                    "mission_title": row[6],
                    "note": row[7]
                }

                self.db.update_log(self.log_id, log_data)
                self.param_content = new_content
                messagebox.showinfo("Success", "Parameter data updated.")
                if self.on_update_callback:
                    self.on_update_callback()
                self.refresh_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update parameters: {e}")

    def update_log_file(self):
        """Updates the log file from a new source."""
        filename = filedialog.askopenfilename(title="Select New Flight Log File")
        if filename:
            try:
                if not self.file_manager:
                    messagebox.showerror("Error", "File manager not available.")
                    return

                new_path = self.file_manager.save_log_file(
                    filename, self.date, self.vehicle, self.flight_no
                )

                # Get current log data to update
                row = self.db.get_log_by_id(self.log_id)
                if not row: return

                log_data = {
                    "flight_no": row[0],
                    "date": row[1],
                    "vehicle_name": row[2],
                    "system_check": row[3],
                    "parameter_changes": row[4],
                    "log_file_path": new_path,
                    "mission_title": row[6],
                    "note": row[7]
                }

                self.db.update_log(self.log_id, log_data)
                self.log_path = new_path
                messagebox.showinfo("Success", "Flight log file updated.")
                if self.on_update_callback:
                    self.on_update_callback()
                self.refresh_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update log file: {e}")

    def edit_log(self):
        """Opens the edit dialog for this flight."""
        def refresh_after_edit():
            if self.on_update_callback:
                self.on_update_callback()
            self.refresh_ui()

        LogEditDialog(self, self.db, self.log_id, on_save_callback=refresh_after_edit)

    def delete_log(self):
        """Deletes this flight log after confirmation."""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this flight log? This action cannot be undone."):
            if self.db.delete_log(self.log_id):
                messagebox.showinfo("Deleted", "Flight log has been deleted.")
                if self.on_update_callback:
                    self.on_update_callback()
                self.destroy()
            else:
                messagebox.showerror("Error", "Failed to delete flight log.")

    def export_params(self):
        """Exports the parameter data to a text file."""
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"params_{self.date}_{self.flight_no}.txt",
        )
        if f:
            with open(f, "w", encoding="utf-8") as file:
                file.write(self.param_content)
            messagebox.showinfo("Success", "Parameters exported.")

    def export_log(self):
        """Exports the log file to a user-selected location."""
        if not self.log_path or not os.path.exists(self.log_path):
            messagebox.showerror("Error", "Log file not found.")
            return
        ext = os.path.splitext(self.log_path)[1]
        f = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=os.path.basename(self.log_path),
        )
        if f:
            shutil.copy2(self.log_path, f)
            messagebox.showinfo("Success", "Log file exported.")
