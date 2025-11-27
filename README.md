# NBT batch conversion GUI

`converter_gui.py` provides a Tkinter interface for batch converting `.nbt` files to `.mcfunction` using the external [JaylyDev/nbt-to-mcstructure](https://github.com/JaylyDev/nbt-to-mcstructure) tool. On startup the GUI downloads the converter repository (if missing) so you only need to pick the folder that already contains your `.nbt` files; `.mcfunction` output is saved in the same folder.

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
- The tool attempts to run the converter directly from the downloaded repo by reading its `bin` entry in `package.json`. If that cannot be determined, it falls back to `npx --yes nbt-to-mcstructure ...` and assumes the binary is reachable via Node/npm.
- Node.js and npm still need to be installed on your system; downloading the repo does not bundle Node itself.

### Windows notes
- Because the converter is invoked directly (without a command template), you generally will not need to edit any paths. If the downloaded repository cannot be parsed, the GUI will fall back to `npx` which relies on Node/npm being on your PATH.
