"""Dialog windows for the Flight Manager application.

This module contains various dialog classes for settings management,
parameter comparison, and viewing flight details.
"""

import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Callable, Dict, List, Optional

from flight_manager.utils import compare_params


class BaseSettingsDialog(tk.Toplevel):
    """Base class for settings dialogs."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        geometry: str = "400x400"
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
            width, height = map(int, geometry.split('x'))
            parent.update_idletasks()
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
            self.geometry(f"{geometry}+{x}+{y}")
        except ValueError:
            # Fallback if geometry string is complex or invalid
            self.geometry(geometry)

        self.transient(parent)
        self.grab_set()


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
        list_frame = ttk.Frame(content_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Listbox (Left)
        self.lb = tk.Listbox(list_frame, height=10, font=("Segoe UI", 11))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=scrollbar.set)

        self.lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Side Buttons (Right)
        side_btn_frame = ttk.Frame(list_frame, padding=(10, 0))
        side_btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(
            side_btn_frame, text="Delete Selected", command=self.delete_item, width=15
        ).pack(fill=tk.X, pady=2)

        self.load_list()

        # --- Bottom Section: Add New ---
        add_frame = ttk.LabelFrame(content_frame, text="Add New Pattern", padding=15)
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
        list_frame = ttk.Frame(content_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        ttk.Label(list_frame, text="Current Vehicles:").pack(anchor="w", pady=(0, 5))

        # Listbox (Left)
        self.lb = tk.Listbox(list_frame, height=10, font=("Segoe UI", 11))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=scrollbar.set)

        self.lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Side Buttons (Right)
        side_btn_frame = ttk.Frame(list_frame, padding=(10, 0))
        side_btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(
            side_btn_frame,
            text="Toggle Archive",
            command=self.toggle_archive,
            width=15
        ).pack(fill=tk.X, pady=2)

        self.load_list()

        # --- Bottom Section: Add New (Moved back to bottom and kept taller) ---
        add_frame = ttk.LabelFrame(content_frame, text="Add New Vehicle", padding=15)
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
        top_frame = ttk.Frame(content_frame)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- Treeview (Left) ---
        tree_frame = ttk.Frame(top_frame)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = ("name", "type", "options")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("options", text="Options")
        
        self.tree.column("name", width=200)
        self.tree.column("type", width=100)
        self.tree.column("options", width=150)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Action Buttons (Right) ---
        btn_frame = ttk.Frame(top_frame, padding=(10, 0))
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(btn_frame, text="▲ Move Up", command=lambda: self.move_item(-1)).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="▼ Move Down", command=lambda: self.move_item(1)).pack(fill=tk.X, pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_item).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Delete", command=self.delete_item).pack(fill=tk.X, pady=2)

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
        
        for name, itype, opts, pid, _ in checklist_items:
            opts_display = opts if opts else ""
            item_id = self.tree.insert("", tk.END, values=(name, itype, opts_display))
            self.checklist_map[item_id] = {
                "id": pid,
                "name": name,
                "type": itype,
                "options": opts
            }

    def create_add_ui(self, parent):
        """Creates the UI for adding new checklist items."""
        ctrl_frame = ttk.LabelFrame(parent, text="Add New Item", padding=10)
        ctrl_frame.pack(fill=tk.X)

        grid_frame = ttk.Frame(ctrl_frame)
        grid_frame.pack(fill=tk.X)

        ttk.Label(grid_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_new = ttk.Entry(grid_frame)
        self.entry_new.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(grid_frame, text="Type:").grid(row=1, column=0, sticky="w", pady=2)
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

        type_combo.bind("<<ComboboxSelected>>", self.toggle_options)
        self.toggle_options()

        grid_frame.columnconfigure(1, weight=1)

        ttk.Button(ctrl_frame, text="Add Item", command=self.add_item).pack(pady=(10, 0), anchor="e")

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
            self.entry_opts.get().strip()
            if itype == "single_select"
            else None
        )

        if val:
            if self.db.add_checklist_item(val, itype, opts):
                self.entry_new.delete(0, tk.END)
                self.entry_opts.delete(0, tk.END)
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

        ttk.Label(main_frame, text="Type:").pack(anchor="w")
        type_var = tk.StringVar(value=data["type"])
        combo_type = ttk.Combobox(
            main_frame, textvariable=type_var, values=["checkbox", "text", "single_select"], state="readonly"
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

        def save_edit():
            new_name = entry_name.get().strip()
            new_type = type_var.get()
            new_opts = entry_opts.get().strip() if new_type == "single_select" else None

            if not new_name:
                messagebox.showwarning("Warning", "Name cannot be empty.", parent=dlg)
                return

            try:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    "UPDATE checklist_items SET name=?, type=?, options=? WHERE id=?",
                    (new_name, new_type, new_opts, data["id"])
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

        ttk.Button(main_frame, text="Save Changes", command=save_edit).pack(pady=10)


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

        self.st = scrolledtext.ScrolledText(self, font=("Consolas", 10))
        self.st.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.st.tag_config("add", foreground="green")
        self.st.tag_config("rem", foreground="red")
        self.st.tag_config("chg", foreground="darkorange")
        self.st.tag_config("head", font=("Consolas", 10, "bold"))

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

    def __init__(self, parent: tk.Widget, db_manager: Any, log_id: int):
        """Initializes the FlightDetailsDialog.

        Args:
            parent: The parent widget.
            db_manager: The database manager instance.
            log_id: The ID of the flight log.
        """
        super().__init__(parent)
        self.db = db_manager
        self.log_id = log_id

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
        self.title(f"Flight Details - {self.date} (ID: {self.flight_no})")
        self.geometry("600x850")

        self.create_widgets(checks_json)

    def create_widgets(self, checks_json: str):
        """Creates the widgets for the dialog."""
        info_frame = ttk.LabelFrame(self, text="Information", padding=10)
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
            note_frame = ttk.LabelFrame(self, text="Note", padding=10)
            note_frame.pack(fill=tk.X, padx=10, pady=5)
            st = scrolledtext.ScrolledText(
                note_frame, height=3, font=("Segoe UI", 9)
            )
            st.insert(tk.END, self.note)
            st.config(state="disabled")
            st.pack(fill=tk.BOTH, expand=True)

        check_frame = ttk.LabelFrame(self, text="Preflight Check", padding=10)
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

        param_frame = ttk.LabelFrame(self, text="Parameter Data", padding=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            param_frame, text="Compare...", command=self.open_compare
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            param_frame, text="Export Params", command=self.export_params
        ).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(self, text="Flight Log File", padding=10)
        log_frame.pack(fill=tk.X, padx=10, pady=5)
        filename = (
            os.path.basename(self.log_path) if self.log_path else "None"
        )
        ttk.Label(log_frame, text=f"File: {filename}").pack(
            side=tk.LEFT, padx=5
        )

        if self.log_path:
            ttk.Button(
                log_frame, text="Export Log", command=self.export_log
            ).pack(side=tk.RIGHT, padx=5)

    def open_compare(self):
        """Opens the comparison dialog for this flight."""
        ComparisonDialog(
            self,
            self.db,
            self.vehicle,
            self.param_content,
            exclude_id=self.log_id,
        )

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
