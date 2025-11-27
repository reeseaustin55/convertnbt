# NBT batch conversion GUI

`converter_gui.py` provides a simple Tkinter interface for batch converting `.nbt` files to `mcfunction` by calling the external [`JaylyDev/nbt-to-mcstructure`](https://github.com/JaylyDev/nbt-to-mcstructure) tool.

## Prerequisites
- Python 3.8+ with Tkinter available (usually included with standard distributions).
- Node.js with the `nbt-to-mcstructure` CLI reachable in your shell, for example via:
  - `npm install -g nbt-to-mcstructure`, or
 - `npx --yes nbt-to-mcstructure ...` (the default command template uses this form).

## Usage
1. Run the GUI:
   ```bash
   python converter_gui.py
   ```
2. Choose the folder containing your `.nbt` files and select an output folder.
3. Adjust the command template if needed. Use `{input}` and `{output}` placeholders to represent the current file and its destination base path. The default template produces mcfunction output via `nbt-to-mcstructure`.
4. Click **Convert** to process every `.nbt` file in the selected folder. Logs from each invocation appear in the log panel.

### Troubleshooting command resolution on Windows
- The GUI uses `shell=True` on Windows so the default `npx` command can locate the installed CLI. If you still see errors like
  `command 'npx' was not found`, install the converter globally (`npm i -g nbt-to-mcstructure`) or replace `npx` in the template
  with the full path to your Node.js installation.

## Command template details
The GUI substitutes `{input}` and `{output}` in the template for each file, then runs the resulting command with `subprocess.run`. This makes it easy to adapt to different versions or installation locations of `nbt-to-mcstructure` without changing the Python code.
