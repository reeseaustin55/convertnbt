"""Command-line utilities for turning NBT data into `.mcfunction` files.

The generated function writes the supplied NBT payload into a storage entry
using a single `data modify storage` command. Optionally, an announcement
`tellraw` line can be appended to provide feedback when the function is run
in-game.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    import nbtlib


def read_snbt(input_path: Path) -> str:
    """Return a single-line SNBT string for the provided file.

    The function accepts compressed or uncompressed `.nbt` files as well as raw
    `.snbt` text files. Newlines are stripped to keep the generated command
    friendly to the `.mcfunction` format.
    """

    if input_path.suffix.lower() == ".snbt":
        return input_path.read_text(encoding="utf-8").replace("\n", "").strip()

    import nbtlib

    nbt_file = nbtlib.load(str(input_path))
    return nbt_file.snbt().replace("\n", "").strip()


def build_mcfunction_lines(
    snbt_payload: str,
    storage: str,
    target_path: str,
    source: Path | None = None,
    announce: bool = False,
) -> List[str]:
    """Create the contents of the `.mcfunction` file.

    Args:
        snbt_payload: The SNBT representation to embed in the command.
        storage: The storage identifier where the payload will be written.
        target_path: The NBT path inside the storage entry.
        source: Optional source path to include as a comment in the output.
        announce: Whether to append a `tellraw` announcing the write.
    """

    lines: List[str] = []
    if source:
        lines.append(f"# Generated from {source}")
    lines.append("# To verify the write, run: data get storage " f"{storage} {target_path}")
    lines.append(f"data modify storage {storage} {target_path} set value {snbt_payload}")

    if announce:
        lines.append(
            'tellraw @s {"text":"Storage write completed","color":"green"}'
        )

    return lines


def convert_file(
    input_path: Path,
    output_path: Path,
    storage: str = "convertnbt:data",
    target_path: str = "data",
    announce: bool = False,
) -> Iterable[str]:
    """Convert an input NBT/SNBT file into `.mcfunction` contents.

    The output is written to ``output_path`` and also returned as an iterable of
    lines. This enables both library-style use and CLI invocation.
    """

    snbt = read_snbt(input_path)
    lines = build_mcfunction_lines(snbt, storage, target_path, input_path, announce)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an NBT or SNBT file into a `.mcfunction` that loads the data "
            "into a storage entry."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the .nbt or .snbt file to convert.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination for the generated .mcfunction file.",
    )
    parser.add_argument(
        "--storage",
        default="convertnbt:data",
        help="Storage identifier that will receive the payload.",
    )
    parser.add_argument(
        "--target",
        default="data",
        help="NBT path within the storage entry (e.g. data.items[0]).",
    )
    parser.add_argument(
        "--announce",
        action="store_true",
        help="Append a tellraw line announcing the write when run.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    convert_file(args.input, args.output, args.storage, args.target, args.announce)


if __name__ == "__main__":
    main()
