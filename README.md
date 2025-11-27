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

#### Option reference (GUI)

* **Storage ID** – Namespaced ID for the storage container to write into when using storage mode. Defaults to `convertnbt:data`.
* **Target path** – NBT path inside the storage to receive the structure payload. Defaults to `data`.
* **Mode** –
  * **Storage** writes the structure NBT into the configured storage/target using `data modify storage ... set value` (or chunked append commands when enabled).
  * **Place blocks** emits `setblock`/`fill` commands that directly place the structure around the executor instead of storing NBT.
* **Append tellraw announcement** – Adds a `tellraw` message at the end of the generated function so you see a success notification in chat after running it.
* **Split into many commands (safer for large structures)** – When enabled in storage mode, breaks the payload into multiple append commands instead of a single very long command to avoid command-length limits. This has no effect in placement mode.
* **Include air blocks when placing** – Placement mode only. If checked, air is written too (matching the original structure); if unchecked, air is skipped so the existing world blocks remain unless overwritten by non-air blocks.
* **Center structure around executor (x/z)** – Placement mode only. Offsets coordinates so the structure is centered on the player/command block that runs the function, instead of placing it strictly relative to one corner.
* **Use fill commands to group rows when placing** – Placement mode only. Collapses contiguous rows of identical blocks into `fill` commands to reduce file size and improve execution speed. Leave unchecked to emit one `setblock` per block.
