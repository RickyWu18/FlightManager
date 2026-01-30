"""Calendar dialog for selecting dates.

This module provides a modal dialog with a calendar widget to allow users
to select a date.
"""

import datetime
import tkinter as tk
from tkinter import ttk
from typing import Callable

from tkcalendar import Calendar


class CalendarDialog(tk.Toplevel):
    """A modal dialog containing a calendar widget."""

    def __init__(self, parent: tk.Widget, callback: Callable[[str], None]):
        """Initializes the CalendarDialog.

        Args:
            parent: The parent widget.
            callback: A function to call with the selected date string.
        """
        super().__init__(parent)
        self.callback = callback
        self.title("Select Date")
        self.geometry("300x250")
        self.transient(parent)
        self.grab_set()

        self.current_date = datetime.date.today()

        self.create_widgets()

    def create_widgets(self):
        """Creates and arranges the widgets in the dialog."""
        # Calendar Widget with specific pattern
        self.cal = Calendar(
            self,
            selectmode="day",
            year=self.current_date.year,
            month=self.current_date.month,
            day=self.current_date.day,
            date_pattern="y-mm-dd",
        )  # Enforce ISO format
        self.cal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame, text="Today", command=self.set_today
        ).pack(side=tk.LEFT, padx=10)
        ttk.Button(
            btn_frame, text="Select", command=self.confirm_date
        ).pack(side=tk.RIGHT, padx=10)
        ttk.Button(
            btn_frame, text="Cancel", command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)

        self.cal.bind("<Double-1>", lambda e: self.confirm_date())

    def set_today(self):
        """Sets the calendar selection to today's date."""
        today = datetime.date.today()
        self.cal.selection_set(today)

    def confirm_date(self):
        """Confirms the selection and calls the callback with the date string."""
        date_str = self.cal.get_date()
        self.callback(date_str)
        self.destroy()