# NBT batch conversion GUI

`converter_gui.py` provides a Tkinter interface for batch converting `.nbt` files to `.mcfunction` using the external [JaylyDev/nbt-to-mcstructure](https://github.com/JaylyDev/nbt-to-mcstructure) tool. On startup the GUI downloads the converter repository and installs its Node dependencies (if missing) so you only need to pick the folder that already contains your `.nbt` files; `.mcfunction` output is saved in the same folder.

## Prerequisites
- Python 3.8+ with Tkinter available (usually included with standard distributions).
- Node.js and npm installed on your system (the converter is a Node CLI). No manual download of the converter is required because the GUI fetches it automatically if absent.
  - On Windows, if `npm` is not found on PATH, the GUI will automatically download a portable Node.js (v18) bundle locally so you can proceed without installing Node globally.

## Usage
1. Run the GUI:
   ```bash
   python converter_gui.py
   ```
2. Choose the folder containing your `.nbt` files.
3. Click **Convert** to process every `.nbt` file in the selected folder. Logs from each invocation appear in the log panel.

### How the converter is prepared
- On startup the GUI downloads `JaylyDev/nbt-to-mcstructure` into a local `nbt-to-mcstructure` folder if it is not present.
- If the local folder is incomplete (for example, missing `package.json`), it is automatically re-downloaded before continuing. Extraction looks for the folder that actually contains `package.json` (even if nested) and skips archive metadata directories so the real package files are restored.
- It then runs `npm install --production` inside that folder (when needed) so the local `node_modules/.bin/nbt-to-mcstructure` command can be executed directly.
- If a local binary cannot be located after install, the tool falls back to `npm exec --yes nbt-to-mcstructure ...`, which uses your installed npm instead of relying on `npx` being on PATH.
- Node.js and npm still need to be installed on your system; downloading the repo does not bundle Node itself. On Windows, if `npm` is missing, the GUI attempts to download a portable Node.js+`npm` bundle automatically and use that for installation **and** for running the converter when `node` is otherwise unavailable.
- When setup fails (for example, when npm is not on PATH), the GUI now emits a detailed diagnostic block showing the converter folder contents, PATH entries, detected `node`/`npm` binaries, and version checks. The same output is also written to `converter_diagnostics.txt` next to `converter_gui.py` so you can attach the file when reporting issues.

### Windows notes
- The GUI prefers the locally installed `node_modules/.bin/nbt-to-mcstructure.cmd` that `npm install` creates. If that binary cannot be used, it falls back to `npm exec --yes nbt-to-mcstructure ...`, so only `npm` needs to be on PATH.
- When `npm` is missing, a portable Node.js+`npm` bundle is downloaded to `embedded_node/` next to `converter_gui.py` and used automatically for installs. The same embedded `node.exe` is used to run the converter when no system-level Node is available.
