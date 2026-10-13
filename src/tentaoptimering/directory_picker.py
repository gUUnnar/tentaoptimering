"""Native directory selection for the packaged, localhost-only application."""

from __future__ import annotations

from pathlib import Path


def choose_directory(initial_directory: str | None = None) -> str | None:
    """Show the operating system's directory chooser and return its selection.

    A browser deliberately cannot expose an arbitrary local directory path.
    The desktop application therefore opens this dialog in its local Python
    process and only returns the selected path to the localhost client.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as error:
        raise RuntimeError("Systemets mappväljare är inte tillgänglig i denna installation.") from error

    initial = Path(initial_directory) if initial_directory else None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            initialdir=str(initial) if initial and initial.is_dir() else None,
            title="Välj källdatakatalog med Excel-underlag",
            mustexist=True,
        )
        return selected or None
    finally:
        root.destroy()
