"""Central font and theme management for the Flight Manager UI.

All named fonts and font-bearing TTK styles are owned by FontManager so that
a single apply_size() call reconfigures the entire UI reactively.
"""

import sys
import tkinter as tk
from tkinter import font, ttk

MAIN = "AppMainFont"
BOLD = "AppBoldFont"
SMALL = "AppSmallFont"
MONO = "AppMonoFont"
MONO_BOLD = "AppMonoBoldFont"

_STANDARD_TK_FONTS = (
    "TkDefaultFont",
    "TkTextFont",
    "TkMenuFont",
    "TkHeadingFont",
    "TkCaptionFont",
    "TkSmallCaptionFont",
)


class FontManager:
    """Owns every named font and font-bearing TTK style in the app."""

    def __init__(self, root: tk.Misc):
        is_win = sys.platform == "win32"
        self._main_family = "Segoe UI" if is_win else "Helvetica"
        self._mono_family = "Consolas" if is_win else "Courier"
        self._root = root
        self._create_named_fonts()

    def _create_named_fonts(self):
        # Small font needs a size relative to the base, so defer the real size
        # to apply_size(). Create placeholders here so widgets can reference
        # the names immediately.
        # Store references to prevent garbage collection from deleting the fonts.
        self._fonts = [
            font.Font(root=self._root, name=MAIN, family=self._main_family, size=10),
            font.Font(root=self._root, name=BOLD, family=self._main_family, size=10, weight="bold"),
            font.Font(root=self._root, name=SMALL, family=self._main_family, size=8),
            font.Font(root=self._root, name=MONO, family=self._mono_family, size=10),
            font.Font(root=self._root, name=MONO_BOLD, family=self._mono_family, size=10, weight="bold"),
        ]

    def apply_size(self, size: int):
        """Reconfigure every named font and TTK style to the given size.

        Widgets referencing the named fonts update automatically.
        """
        small_size = max(8, size - 2)

        font.nametofont(MAIN, root=self._root).configure(size=size)
        font.nametofont(BOLD, root=self._root).configure(size=size)
        font.nametofont(SMALL, root=self._root).configure(size=small_size)
        font.nametofont(MONO, root=self._root).configure(size=size)
        font.nametofont(MONO_BOLD, root=self._root).configure(size=size)

        for name in _STANDARD_TK_FONTS:
            font.nametofont(name, root=self._root).configure(size=size)

        style = ttk.Style()
        style.configure(".", font=(MAIN, size))
        style.configure("Treeview.Heading", font=(MAIN, size, "bold"))
        style.configure("TNotebook.Tab", font=(MAIN, size))
        style.configure("Settings.TButton", font=(MAIN, size))
        style.configure("Settings.TCheckbutton", font=(MAIN, size))
