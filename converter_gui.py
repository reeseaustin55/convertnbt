"""GUI tool to batch convert .nbt files to mcfunction using JaylyDev/nbt-to-mcstructure.

The GUI wraps an external Node.js CLI (https://github.com/JaylyDev/nbt-to-mcstructure).
It expects the CLI to be available via the command template and will invoke it once
per .nbt file in the selected folder.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


class ConverterGUI(tk.Tk):
    """Simple Tkinter GUI for converting NBT files with a configurable CLI template."""

    def __init__(self) -> None:
        super().__init__()
        self.title("NBT to mcfunction")
        self.resizable(False, False)

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.command_template_var = tk.StringVar(
            value=(
                "npx --yes nbt-to-mcstructure --input \"{input}\" "
                "--output \"{output}\" --format mcfunction"
            )
        )

        self._build_layout()
        self.convert_thread: threading.Thread | None = None

    def _build_layout(self) -> None:
        padding = {"padx": 6, "pady": 4}

        # Source folder
        tk.Label(self, text="NBT folder:").grid(row=0, column=0, sticky="w", **padding)
        tk.Entry(self, textvariable=self.source_var, width=55).grid(
            row=0, column=1, **padding
        )
        tk.Button(self, text="Browse", command=self._choose_source).grid(
            row=0, column=2, **padding
        )

        # Output folder
        tk.Label(self, text="Output folder:").grid(row=1, column=0, sticky="w", **padding)
        tk.Entry(self, textvariable=self.output_var, width=55).grid(
            row=1, column=1, **padding
        )
        tk.Button(self, text="Browse", command=self._choose_output).grid(
            row=1, column=2, **padding
        )

        # Command template
        tk.Label(self, text="Command template:").grid(
            row=2, column=0, sticky="nw", **padding
        )
        tk.Label(
            self,
            text=(
                "Use {input} and {output} placeholders.\n"
                "Defaults to calling npx nbt-to-mcstructure for mcfunction output."
            ),
            justify="left",
        ).grid(row=2, column=2, sticky="w", **padding)
        tk.Entry(self, textvariable=self.command_template_var, width=55).grid(
            row=2, column=1, **padding
        )

        # Convert button
        self.convert_button = tk.Button(self, text="Convert", command=self._start_conversion)
        self.convert_button.grid(row=3, column=0, columnspan=3, **padding)

        # Log output
        tk.Label(self, text="Log:").grid(row=4, column=0, sticky="nw", **padding)
        self.log_widget = scrolledtext.ScrolledText(self, width=80, height=18, state="disabled")
        self.log_widget.grid(row=4, column=1, columnspan=2, **padding)

    def _choose_source(self) -> None:
        folder = filedialog.askdirectory(title="Select folder containing .nbt files")
        if folder:
            self.source_var.set(folder)

    def _choose_output(self) -> None:
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_var.set(folder)

    def _start_conversion(self) -> None:
        if self.convert_thread and self.convert_thread.is_alive():
            messagebox.showinfo("Conversion", "Conversion already in progress.")
            return

        source = self.source_var.get().strip()
        output = self.output_var.get().strip()
        cmd_template = self.command_template_var.get().strip()

        if not source or not os.path.isdir(source):
            messagebox.showerror("Invalid folder", "Please choose a valid source folder.")
            return
        if not output:
            messagebox.showerror("Invalid output", "Please choose an output folder.")
            return

        nbt_files = [
            os.path.join(source, f)
            for f in os.listdir(source)
            if f.lower().endswith(".nbt")
        ]
        if not nbt_files:
            messagebox.showinfo("No files", "No .nbt files found in the selected folder.")
            return

        os.makedirs(output, exist_ok=True)
        self._append_log("> Starting conversion for %d file(s)...\n" % len(nbt_files))
        self.convert_button.configure(state="disabled")

        self.convert_thread = threading.Thread(
            target=self._convert_files, args=(nbt_files, output, cmd_template), daemon=True
        )
        self.convert_thread.start()

    def _convert_files(self, nbt_files: list[str], output: str, cmd_template: str) -> None:
        shell = os.name == "nt"
        try:
            for path in nbt_files:
                try:
                    dest = os.path.join(
                        output, os.path.splitext(os.path.basename(path))[0]
                    )
                    cmd = cmd_template.format(input=path, output=dest)
                except KeyError as exc:
                    self._append_log(
                        f"Command template is missing placeholder {{{exc.args[0]}}}.\n"
                    )
                    break

                self._append_log(f"Running: {cmd}\n")
                try:
                    args = cmd if shell else shlex.split(cmd, posix=os.name != "nt")
                    result = subprocess.run(
                        args, shell=shell, capture_output=True, text=True, check=False
                    )
                except FileNotFoundError:
                    missing = cmd.split()[0]
                    hint = "Use npm i -g nbt-to-mcstructure or adjust the command template."
                    self._append_log(
                        f"Error converting {path}: command '{missing}' was not found. {hint}\n"
                    )
                    break
                except Exception as exc:  # noqa: BLE001 (log and continue)
                    self._append_log(f"Error converting {path}: {exc}\n")
                    continue

                if result.stdout:
                    self._append_log(result.stdout)
                if result.stderr:
                    self._append_log(result.stderr)
                if result.returncode != 0:
                    self._append_log(
                        f"Command failed with exit code {result.returncode} for {path}\n"
                    )
                else:
                    self._append_log(f"✔ Converted {path}\n")
        finally:
            self._append_log("\nFinished.\n")
            self.convert_button.configure(state="normal")

    def _append_log(self, message: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert(tk.END, message)
        self.log_widget.see(tk.END)
        self.log_widget.configure(state="disabled")


def main() -> None:
    app = ConverterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
