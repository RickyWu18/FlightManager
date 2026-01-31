#!/usr/bin/env python3
"""Entry point for the Flight Manager application."""

import tkinter as tk

from flight_manager.ui.main_window import FlightManagerApp


def main():
    """Initializes and runs the Flight Manager application."""
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    app = FlightManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
