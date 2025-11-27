# convertNBT

A small utility that converts NBT or SNBT data into a Minecraft `.mcfunction` file that loads the payload into a storage container with a single `data modify storage` command.

## Requirements

* Python 3.9+
* [`nbtlib`](https://github.com/vberlier/nbtlib) (install via `pip install -r requirements.txt`)

## Usage

Run the converter from the repository root:

```bash
python -m convertnbt.cli --input path/to/input.nbt --output load.mcfunction \
  --storage example:store --target data
```

Key options:

* `--input` – path to a `.nbt` (compressed or uncompressed) or `.snbt` file.
* `--output` – destination path for the generated `.mcfunction` file.
* `--storage` – storage ID to write into (defaults to `convertnbt:data`).
* `--target` – NBT path inside the storage (defaults to `data`).
* `--announce` – append a `tellraw` line announcing success when the function runs.

The generated file contains helpful comments and a single `data modify storage` command that injects the supplied NBT payload into the chosen storage location.
