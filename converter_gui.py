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
import sys
import tempfile
import zipfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Callable
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

        # If the repository exists but looks incomplete (no package.json), refresh it.
        package_json = repo_dir / "package.json"
        if not package_json.exists():
            try:
                self._append_log(
                    "Converter package.json missing; re-downloading repository...\n"
                )
                download_and_extract_repo(repo_dir)
                self._append_log("Redownload complete.\n")
            except URLError as exc:
                self._append_log(f"Failed to download repository: {exc}\n")
            except Exception as exc:  # noqa: BLE001 (log unexpected failures)
                self._append_log(f"Unexpected error downloading repository: {exc}\n")

        if not ensure_converter_dependencies(repo_dir, self._append_log):
            log_environment_diagnostics(repo_dir, self._append_log)
            self.convert_button.configure(text="Converter unavailable", state="disabled")
            return

        self.converter_command = resolve_converter_command(repo_dir)
        if self.converter_command is None:
            self._append_log(
                "Could not determine converter command. Ensure Node.js/npm are installed.\n"
            )
            log_environment_diagnostics(repo_dir, self._append_log)
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
                    shell = os.name == "nt" and command and command[0].lower().endswith(".cmd")

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

        # Prefer the directory that actually contains package.json anywhere
        # inside it (not only direct children) because some GitHub archives can
        # nest the repository inside another folder, and macOS adds metadata
        # directories like __MACOSX.
        candidate_dirs = [p.parent for p in Path(tmp).rglob("package.json")]
        chosen_dir = None
        for path in candidate_dirs:
            if path.is_dir():
                chosen_dir = path
                break

        if chosen_dir is None:
            chosen_dir = extracted_dirs[0]

        shutil.copytree(chosen_dir, target_dir, dirs_exist_ok=True)


def ensure_converter_dependencies(repo_dir: Path, log: Callable[[str], None]) -> bool:
    """Ensure the downloaded converter has its Node dependencies installed."""

    package_json = repo_dir / "package.json"
    if not package_json.exists():
        contents = ", ".join(p.name for p in repo_dir.iterdir()) if repo_dir.exists() else ""
        log(
            "Converter package.json was not found after download. "
            "Folder contents: %s\n" % (contents or "<empty>")
        )
        return False

    if has_local_binary(repo_dir):
        return True

    npm_cmd = resolve_npm_command()
    if npm_cmd is None and os.name == "nt":
        log(
            "npm was not found on PATH. Attempting to download an embedded Node.js runtime...\n"
        )
        npm_cmd = ensure_embedded_node(log)

    if npm_cmd is None:
        log("npm was not found on PATH. Please install Node.js/npm and restart the tool.\n")
        return False

    log("Installing converter dependencies (npm install)...\n")
    result = subprocess.run(
        [npm_cmd, "install", "--production"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(result.stderr)

    if result.returncode != 0:
        log("npm install failed; see output above.\n")
        return False

    if not has_local_binary(repo_dir):
        log("npm install completed but converter binary was not found.\n")
        return False

    return True


def package_bin_path(repo_dir: Path) -> Path | None:
    """Return the CLI path from package.json `bin` if available."""

    package_json = repo_dir / "package.json"
    if not package_json.exists():
        return None

    try:
        data = json.loads(package_json.read_text())
        bin_entry = data.get("bin")
        if isinstance(bin_entry, str):
            return repo_dir / bin_entry
        if isinstance(bin_entry, dict):
            first_bin = next(iter(bin_entry.values()))
            return repo_dir / first_bin
    except Exception:  # noqa: BLE001 (best-effort helper)
        return None

    return None


def local_bin_path(repo_dir: Path) -> Path | None:
    """Return the node_modules/.bin executable if present."""

    bin_dir = repo_dir / "node_modules" / ".bin"
    candidates = [
        bin_dir / "nbt-to-mcstructure",
        bin_dir / "nbt-to-mcstructure.cmd",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def has_local_binary(repo_dir: Path) -> bool:
    """Check whether a usable local binary exists."""

    local_bin = local_bin_path(repo_dir)
    if local_bin is not None:
        return True

    package_bin = package_bin_path(repo_dir)
    return package_bin is not None and package_bin.exists()


def resolve_npm_command() -> str | None:
    """Locate npm on the current platform."""

    embedded_npm = embedded_npm_path()
    if embedded_npm and embedded_npm.exists():
        return str(embedded_npm)

    if os.name == "nt":
        for name in ("npm.cmd", "npm.exe", "npm"):
            path = shutil.which(name)
            if path:
                return path
        return None

    return shutil.which("npm")


def resolve_converter_command(repo_dir: Path) -> list[str] | str | None:
    """Determine the command used to run the converter.

    Preference order:
    1. Use the locally installed binary under node_modules/.bin.
    2. Use the package.json `bin` entry directly via `node`.
    3. Fall back to `npm exec` with the global `nbt-to-mcstructure` package if
       the local repo cannot be used.
    """

    local_bin = local_bin_path(repo_dir)
    if local_bin is not None:
        if os.name == "nt" and local_bin.suffix.lower() == ".cmd":
            return [str(local_bin)]
        return [str(local_bin)]

    package_bin = package_bin_path(repo_dir)
    if package_bin is not None:
        return ["node", str(package_bin)]

    npm_cmd = resolve_npm_command()
    if npm_cmd is None:
        return None

    # Prefer npm exec so we do not rely on npx being on PATH
    return [npm_cmd, "exec", "--yes", "nbt-to-mcstructure"]


def build_command(template: list[str] | str, input_path: str, output_path: str) -> list[str] | str:
    """Inject input/output paths into the converter command template."""

    if isinstance(template, list):
        return template + [
            "--input",
            input_path,
            "--output",
            output_path,
            "--format",
            "mcfunction",
        ]

    return template.format(input=input_path, output=output_path)


def log_environment_diagnostics(
    repo_dir: Path, log: Callable[[str], None], *, write_file: bool = True
) -> None:
    """Log environment details to help diagnose converter setup failures.

    When *write_file* is True, the diagnostics are also written to
    ``converter_diagnostics.txt`` next to this script so they can be shared
    without copy/paste loss.
    """

    buffer: list[str] = []

    def log_and_capture(message: str) -> None:
        buffer.append(message)
        log(message)

    log_and_capture("\n==== Environment diagnostics ===\n")
    log_and_capture(f"Platform: os.name={os.name}, sys.platform={sys.platform}\n")
    log_and_capture(f"Python version: {sys.version.split()[0]}\n")
    log_and_capture(f"Working directory: {Path.cwd()}\n")
    log_and_capture(
        f"Converter directory: {repo_dir} (exists: {repo_dir.exists()})\n"
    )

    # Summarize prerequisite visibility first so users can spot the root cause quickly.
    node_cmd = shutil.which("node") or shutil.which("node.exe") or shutil.which("node.cmd")
    npm_cmd = resolve_npm_command()
    log_and_capture(
        "Prerequisite summary: node=%s, npm=%s\n"
        % (node_cmd or "not found", npm_cmd or "not found")
    )
    if EMBEDDED_NODE_DIR.exists():
        log_and_capture(f"Embedded Node directory: {EMBEDDED_NODE_DIR}\n")

    if repo_dir.exists():
        try:
            entries = sorted(
                f"{p.name}/" if p.is_dir() else p.name for p in repo_dir.iterdir()
            )
            log_and_capture("Repo contents: %s\n" % (", ".join(entries) or "<empty>"))
        except Exception as exc:  # noqa: BLE001 (best-effort diagnostics)
            log_and_capture(f"Repo listing failed: {exc}\n")

        package_json = repo_dir / "package.json"
        log_and_capture(f"package.json present: {package_json.exists()}\n")
        log_and_capture(f"node_modules present: {(repo_dir / 'node_modules').exists()}\n")
        log_and_capture(f"Local binary: {local_bin_path(repo_dir) or 'not found'}\n")
    else:
        log_and_capture("Converter directory is missing entirely.\n")

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    log_and_capture("PATH entries:\n")
    for entry in path_entries:
        log_and_capture(f" - {entry or '<empty>'}\n")

    for name in ("node", "node.exe", "node.cmd"):
        log_and_capture(f"which {name}: {shutil.which(name) or 'not found'}\n")

    for name in ("npm", "npm.cmd", "npm.exe"):
        log_and_capture(f"which {name}: {shutil.which(name) or 'not found'}\n")

    if npm_cmd:
        log_and_capture(f"Using npm command: {npm_cmd}\n")
        try:
            npm_version = subprocess.run(
                [npm_cmd, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if npm_version.stdout:
                log_and_capture(f"npm --version stdout: {npm_version.stdout}")
            if npm_version.stderr:
                log_and_capture(f"npm --version stderr: {npm_version.stderr}")
        except Exception as exc:  # noqa: BLE001 (best-effort diagnostics)
            log_and_capture(f"npm --version failed: {exc}\n")

    if node_cmd:
        log_and_capture(f"Using node command: {node_cmd}\n")
        try:
            node_version = subprocess.run(
                [node_cmd, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if node_version.stdout:
                log_and_capture(f"node --version stdout: {node_version.stdout}")
            if node_version.stderr:
                log_and_capture(f"node --version stderr: {node_version.stderr}")
        except Exception as exc:  # noqa: BLE001 (best-effort diagnostics)
            log_and_capture(f"node --version failed: {exc}\n")

    log_and_capture("===============================\n")

    if write_file:
        try:
            diag_path = Path(__file__).resolve().parent / "converter_diagnostics.txt"
            diag_path.write_text("".join(buffer))
            log(
                f"Saved diagnostics to {diag_path}. Share this file when reporting issues.\n"
            )
        except Exception as exc:  # noqa: BLE001 (best-effort diagnostics)
            log(f"Could not write diagnostics file: {exc}\n")


def ensure_embedded_node(log: Callable[[str], None]) -> str | None:
    """Download a portable Node.js+npm bundle on Windows when npm is missing."""

    if os.name != "nt":
        return None

    npm_path = embedded_npm_path()
    if npm_path and npm_path.exists():
        return str(npm_path)

    url = "https://nodejs.org/dist/v18.20.4/node-v18.20.4-win-x64.zip"
    try:
        EMBEDDED_NODE_DIR.mkdir(parents=True, exist_ok=True)
        log("Downloading embedded Node.js (v18.20.4)...\n")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = Path(tmp.name)
            with urlopen(url) as response, open(tmp_path, "wb") as handle:
                shutil.copyfileobj(response, handle)

        with zipfile.ZipFile(tmp_path) as zip_ref:
            zip_ref.extractall(EMBEDDED_NODE_DIR)
        tmp_path.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001 (best-effort helper)
        log(f"Failed to download embedded Node.js: {exc}\n")
        return None

    npm_path = embedded_npm_path()
    if npm_path and npm_path.exists():
        log(f"Embedded Node.js ready at {EMBEDDED_NODE_DIR}.\n")
        return str(npm_path)

    log("Embedded Node.js download completed but npm was not found.\n")
    return None


def embedded_npm_path() -> Path | None:
    """Return the npm.cmd path within the embedded Node folder, if any."""

    if not EMBEDDED_NODE_DIR.exists():
        return None

    for npm_candidate in EMBEDDED_NODE_DIR.rglob("npm.cmd"):
        return npm_candidate
    for npm_candidate in EMBEDDED_NODE_DIR.rglob("npm.exe"):
        return npm_candidate
    for npm_candidate in EMBEDDED_NODE_DIR.rglob("npm"):
        if npm_candidate.is_file():
            return npm_candidate
    return None


def main() -> None:
    app = ConverterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
EMBEDDED_NODE_DIR = Path(__file__).resolve().parent / "embedded_node"

