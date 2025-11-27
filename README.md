# NBT batch conversion GUI

`converter_gui.py` provides a Tkinter interface for batch converting `.nbt` files to `.mcfunction` using the external [JaylyDev/nbt-to-mcstructure](https://github.com/JaylyDev/nbt-to-mcstructure) tool. On startup the GUI downloads the converter repository and installs its Node dependencies (if missing) so you only need to pick the folder that already contains your `.nbt` files; `.mcfunction` output is saved in the same folder.

## Prerequisites
- Python 3.8+ with Tkinter available (usually included with standard distributions).
- Node.js and npm installed on your system (the converter is a Node CLI). No manual download of the converter is required because the GUI fetches it automatically if absent.

## Usage
1. Run the GUI:
   ```bash
   python converter_gui.py
   ```
2. Choose the folder containing your `.nbt` files.
3. Click **Convert** to process every `.nbt` file in the selected folder. Logs from each invocation appear in the log panel.

### How the converter is prepared
- On startup the GUI downloads `JaylyDev/nbt-to-mcstructure` into a local `nbt-to-mcstructure` folder if it is not present.
- If the local folder is incomplete (for example, missing `package.json`), it is automatically re-downloaded before continuing, skipping archive metadata folders so the real package files are restored.
- It then runs `npm install --production` inside that folder (when needed) so the local `node_modules/.bin/nbt-to-mcstructure` command can be executed directly—no `npx` dependency.
- If a local binary cannot be located after install, the tool falls back to `npx --yes nbt-to-mcstructure ...` and assumes the binary is reachable via Node/npm.
- Node.js and npm still need to be installed on your system; downloading the repo does not bundle Node itself.

### Windows notes
- The GUI prefers the locally installed `node_modules/.bin/nbt-to-mcstructure.cmd` that `npm install` creates, so `npx` does not need to be available on PATH. If the local binary is missing, it falls back to `npx`, which still requires Node/npm on PATH.
