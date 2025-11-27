"""Simple Tkinter GUI for converting NBT/SNBT files to `.mcfunction` files.

The interface lets users pick a folder containing `.nbt` or `.snbt` files.
Each file is converted to a `.mcfunction` with the same base name in the
selected folder.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__ in {None, ""}:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from convertnbt.cli import convert_file
else:
    from .cli import convert_file


class ConverterGUI:
    """Tkinter-based GUI for batch converting NBT files in a folder."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NBT to mcfunction Converter")
        self.root.geometry("520x360")
        self.root.minsize(480, 320)

        self.folder_var = tk.StringVar()
        self.storage_var = tk.StringVar(value="convertnbt:data")
        self.target_var = tk.StringVar(value="data")
        self.announce_var = tk.BooleanVar(value=False)
        self.chunk_var = tk.BooleanVar(value=True)
        self.mode_var = tk.StringVar(value="storage")
        self.include_air_var = tk.BooleanVar(value=False)
        self.center_var = tk.BooleanVar(value=False)
        self.fill_var = tk.BooleanVar(value=False)

        self._build_layout()

    def _build_layout(self) -> None:
        padding = {"padx": 10, "pady": 6}

        folder_frame = ttk.LabelFrame(self.root, text="Folder")
        folder_frame.pack(fill="x", padx=12, pady=10)

        folder_row = ttk.Frame(folder_frame)
        folder_row.pack(fill="x", padx=8, pady=8)

        ttk.Label(folder_row, text="NBT folder:").pack(side="left")
        folder_entry = ttk.Entry(folder_row, textvariable=self.folder_var)
        folder_entry.pack(side="left", fill="x", expand=True, padx=(6, 8))

        ttk.Button(folder_row, text="Browse", command=self.select_folder).pack(side="left")

        options_frame = ttk.LabelFrame(self.root, text="Options")
        options_frame.pack(fill="x", padx=12, pady=(0, 10))

        storage_row = ttk.Frame(options_frame)
        storage_row.pack(fill="x", **padding)
        ttk.Label(storage_row, text="Storage ID:").pack(side="left")
        ttk.Entry(storage_row, textvariable=self.storage_var).pack(side="left", fill="x", expand=True, padx=(8, 0))

        target_row = ttk.Frame(options_frame)
        target_row.pack(fill="x", **padding)
        ttk.Label(target_row, text="Target path:").pack(side="left")
        ttk.Entry(target_row, textvariable=self.target_var).pack(side="left", fill="x", expand=True, padx=(12, 0))

        mode_row = ttk.Frame(options_frame)
        mode_row.pack(fill="x", **padding)
        ttk.Label(mode_row, text="Mode:").pack(side="left")
        ttk.Radiobutton(mode_row, text="Storage", value="storage", variable=self.mode_var).pack(side="left", padx=(6, 12))
        ttk.Radiobutton(mode_row, text="Place blocks", value="place", variable=self.mode_var).pack(side="left")

        announce_row = ttk.Frame(options_frame)
        announce_row.pack(fill="x", **padding)
        ttk.Checkbutton(announce_row, text="Append tellraw announcement", variable=self.announce_var).pack(side="left")

        chunk_row = ttk.Frame(options_frame)
        chunk_row.pack(fill="x", **padding)
        ttk.Checkbutton(
            chunk_row,
            text="Split into many commands (safer for large structures)",
            variable=self.chunk_var,
        ).pack(side="left")

        air_row = ttk.Frame(options_frame)
        air_row.pack(fill="x", **padding)
        ttk.Checkbutton(
            air_row,
            text="Include air blocks when placing",
            variable=self.include_air_var,
        ).pack(side="left")

        center_row = ttk.Frame(options_frame)
        center_row.pack(fill="x", **padding)
        ttk.Checkbutton(
            center_row,
            text="Center structure around executor (x/z)",
            variable=self.center_var,
        ).pack(side="left")

        fill_row = ttk.Frame(options_frame)
        fill_row.pack(fill="x", **padding)
        ttk.Checkbutton(
            fill_row,
            text="Use fill commands to group rows when placing",
            variable=self.fill_var,
        ).pack(side="left")

        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(action_frame, text="Convert", command=self.convert_folder).pack(side="right")

        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.log = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

    def append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def select_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Select folder containing NBT files")
        if chosen:
            self.folder_var.set(chosen)

    def convert_folder(self) -> None:
        folder_value = self.folder_var.get().strip()
        if not folder_value:
            messagebox.showerror("Missing folder", "Please choose a folder containing .nbt or .snbt files.")
            return

        folder_path = Path(folder_value)
        if not folder_path.exists() or not folder_path.is_dir():
            messagebox.showerror("Invalid folder", "The selected path is not a folder.")
            return

        files = [p for p in folder_path.iterdir() if p.suffix.lower() in {".nbt", ".snbt"}]
        if not files:
            messagebox.showinfo("No files", "No .nbt or .snbt files were found in the selected folder.")
            return

        storage = self.storage_var.get().strip() or "convertnbt:data"
        target = self.target_var.get().strip() or "data"
        announce = self.announce_var.get()
        chunk = self.chunk_var.get()
        mode = self.mode_var.get()
        include_air = self.include_air_var.get()
        center = self.center_var.get()
        use_fill = self.fill_var.get()

        successes = 0
        failures: list[str] = []

        for file_path in files:
            output_path = file_path.with_suffix(".mcfunction")
            try:
                convert_file(
                    file_path,
                    output_path,
                    storage,
                    target,
                    announce,
                    chunk,
                    mode,
                    include_air,
                    center,
                    use_fill,
                )
            except Exception as exc:  # pragma: no cover - GUI feedback
                failures.append(f"{file_path.name}: {exc}")
                self.append_log(f"❌ Failed {file_path.name}: {exc}")
            else:
                successes += 1
                self.append_log(f"✅ Wrote {output_path.name}")

        summary_lines = [f"Converted {successes} file(s)"]
        if failures:
            summary_lines.append(f"Encountered {len(failures)} error(s)")

        messagebox.showinfo("Conversion complete", "\n".join(summary_lines))

    def run(self) -> None:
        self.root.mainloop()


def launch_gui() -> None:
    """Start the converter GUI."""

    root = tk.Tk()
    ConverterGUI(root).run()


if __name__ == "__main__":
    launch_gui()
