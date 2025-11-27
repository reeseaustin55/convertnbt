# convertNBT

A small utility that converts NBT or SNBT data into a Minecraft `.mcfunction` file. You can either load the payload into a storage container with `data modify storage` or directly place every block with `setblock` commands.

## Requirements

* Python 3.9+
* [`nbtlib`](https://github.com/vberlier/nbtlib) (install via `pip install -r requirements.txt`)

## Usage

### Command line

Run the converter from the repository root:

```bash
python -m convertnbt.cli --input path/to/input.nbt --output load.mcfunction \
  --storage example:store --target data [--chunk] [--mode place] [--include-air] \
  [--center] [--fill]
```

Key options:

* `--input` – path to a `.nbt` (compressed or uncompressed) or `.snbt` file.
* `--output` – destination path for the generated `.mcfunction` file.
* `--storage` – storage ID to write into (defaults to `convertnbt:data`).
* `--target` – NBT path inside the storage (defaults to `data`).
* `--announce` – append a `tellraw` line announcing success when the function runs.
* `--chunk` – emit many smaller `data modify ... append` commands instead of a
  single massive `set value` line (recommended for large structures that exceed
  command length limits).
* `--mode` – choose `storage` (default) to write into a storage entry or `place`
  to emit placement commands.
* `--include-air` – when using placement mode, also emit commands for air blocks
  instead of skipping them.
* `--center` – offset placement so the structure is centered on the executor on
  the X/Z axes (helpful for symmetric buildings).
* `--fill` – group identical rows of blocks into `fill` commands instead of
  emitting one `setblock` per block.

The generated file contains helpful comments and a single `data modify storage` command that injects the supplied NBT payload into the chosen storage location.

### GUI

A basic Tkinter GUI is available for batch converting every `.nbt` or `.snbt` file in a folder. Each converted file is written back to the same folder with the `.mcfunction` extension.

Launch it with:

```bash
python -m convertnbt.gui
```

Steps:

1. Click **Browse** and choose the folder containing your NBT/SNBT files.
2. Choose **Storage** mode to write into data storage or **Place blocks** to emit placement commands (optionally include air blocks, centering, and fill grouping).
3. Adjust the **Storage ID**, **Target path**, **tellraw**, or chunking toggles as needed.
4. Click **Convert** to write `.mcfunction` files alongside each source file. Progress is reported in the on-screen log and a summary dialog.
