"""GUI tool to batch convert .nbt files to mcfunction using JaylyDev/nbt-to-mcstructure.

The GUI wraps the Node.js CLI from https://github.com/JaylyDev/nbt-to-mcstructure.
On startup it downloads the repository (if missing) so the converter can be run
locally without extra setup. Users only select the folder that contains `.nbt`
files; converted mcfunction output is written alongside the source files.
"""
from __future__ import annotations

import os
import shlex
import json
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


class ConverterGUI(tk.Tk):
    """Tkinter GUI for converting NBT files with minimal user input."""

    def __init__(self) -> None:
        super().__init__()
        self.title("NBT to mcfunction")
        self.resizable(False, False)

        self.source_var = tk.StringVar()
        self.convert_thread: threading.Thread | None = None
        self.converter_command: list[str] | str | None = None
        self.converter_ready = False

        self._build_layout()
        self._prepare_converter_async()

    def _build_layout(self) -> None:
        padding = {"padx": 6, "pady": 4}

        # Source folder
        tk.Label(self, text="NBT folder:").grid(row=0, column=0, sticky="w", **padding)
        tk.Entry(self, textvariable=self.source_var, width=60).grid(
            row=0, column=1, **padding
        )
        tk.Button(self, text="Browse", command=self._choose_source).grid(
            row=0, column=2, **padding
        )

        # Convert button
        self.convert_button = tk.Button(
            self,
            text="Preparing converter...",
            state="disabled",
            command=self._start_conversion,
        )
        self.convert_button.grid(row=1, column=0, columnspan=3, **padding)

        # Log output
        tk.Label(self, text="Log:").grid(row=2, column=0, sticky="nw", **padding)
        self.log_widget = scrolledtext.ScrolledText(self, width=80, height=18, state="disabled")
        self.log_widget.grid(row=2, column=1, columnspan=2, **padding)

    def _choose_source(self) -> None:
        folder = filedialog.askdirectory(title="Select folder containing .nbt files")
        if folder:
            self.source_var.set(folder)

    def _prepare_converter_async(self) -> None:
        thread = threading.Thread(target=self._prepare_converter, daemon=True)
        thread.start()

    def _prepare_converter(self) -> None:
        """Download the converter repo (if missing) and determine the CLI command."""

        repo_dir = Path(__file__).resolve().parent / "nbt-to-mcstructure"
        if repo_dir.exists():
            self._append_log("Converter repository already present.\n")
        else:
            try:
                self._append_log("Downloading converter repository...\n")
                download_and_extract_repo(repo_dir)
                self._append_log("Download complete.\n")
            except URLError as exc:
                self._append_log(f"Failed to download repository: {exc}\n")
            except Exception as exc:  # noqa: BLE001 (log unexpected failures)
                self._append_log(f"Unexpected error downloading repository: {exc}\n")

        self.converter_command = resolve_converter_command(repo_dir)
        if self.converter_command is None:
            self._append_log(
                "Could not determine converter command. You may need Node.js/npm installed.\n"
            )
            self.convert_button.configure(text="Converter unavailable", state="disabled")
            return

        self.converter_ready = True
        self.convert_button.configure(text="Convert", state="normal")
        self._append_log("Converter ready. Select an NBT folder and click Convert.\n")

    def _start_conversion(self) -> None:
        if not self.converter_ready:
            messagebox.showerror(
                "Converter not ready",
                "Still preparing the converter. Please wait a moment and try again.",
            )
            return

        if self.convert_thread and self.convert_thread.is_alive():
            messagebox.showinfo("Conversion", "Conversion already in progress.")
            return

        source = self.source_var.get().strip()

        if not source or not os.path.isdir(source):
            messagebox.showerror("Invalid folder", "Please choose a valid source folder.")
            return

        nbt_files = [
            os.path.join(source, f)
            for f in os.listdir(source)
            if f.lower().endswith(".nbt")
        ]
        if not nbt_files:
            messagebox.showinfo("No files", "No .nbt files found in the selected folder.")
            return

        self._append_log("> Starting conversion for %d file(s)...\n" % len(nbt_files))
        self.convert_button.configure(state="disabled")

        self.convert_thread = threading.Thread(
            target=self._convert_files, args=(nbt_files,), daemon=True
        )
        self.convert_thread.start()

    def _convert_files(self, nbt_files: list[str]) -> None:
        try:
            for path in nbt_files:
                dest = os.path.splitext(path)[0]
                command = build_command(self.converter_command, path, dest)

                if isinstance(command, str):
                    display_cmd = command
                    shell = os.name == "nt"
                    args = command if shell else shlex.split(command, posix=os.name != "nt")
                else:
                    display_cmd = " ".join(shlex.quote(part) for part in command)
                    args = command
                    shell = False

                self._append_log(f"Running: {display_cmd}\n")
                try:
                    result = subprocess.run(
                        args, shell=shell, capture_output=True, text=True, check=False
                    )
                except FileNotFoundError as exc:
                    missing = command[0] if isinstance(command, list) else str(command).split()[0]
                    self._append_log(
                        f"Error converting {path}: command '{missing}' was not found ({exc}).\n"
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


def download_and_extract_repo(target_dir: Path) -> None:
    """Download and extract the converter repository to *target_dir*.

    The download is pulled from the main branch zip archive. If the directory already
    exists, it is replaced.
    """

    if target_dir.exists():
        shutil.rmtree(target_dir)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "nbt-to-mcstructure.zip"
        url = "https://github.com/JaylyDev/nbt-to-mcstructure/archive/refs/heads/main.zip"
        with urlopen(url) as response, open(zip_path, "wb") as handle:
            shutil.copyfileobj(response, handle)

        shutil.unpack_archive(str(zip_path), tmp)
        extracted_dirs = [p for p in Path(tmp).iterdir() if p.is_dir()]
        if not extracted_dirs:
            raise RuntimeError("Downloaded archive did not contain any folders")

        shutil.move(str(extracted_dirs[0]), target_dir)


def resolve_converter_command(repo_dir: Path) -> list[str] | str | None:
    """Determine the command used to run the converter.

    Preference order:
    1. Use the locally downloaded repository by reading its package.json `bin` entry.
    2. Fall back to the global/npx-installed `nbt-to-mcstructure` binary.
    """

    package_json = repo_dir / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            bin_entry = data.get("bin")
            if isinstance(bin_entry, str):
                return ["node", str(repo_dir / bin_entry)]
            if isinstance(bin_entry, dict):
                first_bin = next(iter(bin_entry.values()))
                return ["node", str(repo_dir / first_bin)]
        except Exception:  # noqa: BLE001 (fallback handled below)
            pass

    # Fallback to npx if local repo parsing failed or package.json missing
    return "npx --yes nbt-to-mcstructure --input \"{input}\" --output \"{output}\" --format mcfunction"


def build_command(template: list[str] | str, input_path: str, output_path: str) -> list[str] | str:
    """Inject input/output paths into the converter command template."""

    if isinstance(template, list):
        return template + ["--input", input_path, "--output", output_path, "--format", "mcfunction"]

    return template.format(input=input_path, output=output_path)


def main() -> None:
    app = ConverterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
