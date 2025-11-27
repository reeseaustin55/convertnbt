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


def parse_snbt_tag(snbt: str):
    """Return an nbtlib tag from an SNBT string, trying multiple helpers.

    nbtlib exposes different parsing helpers across versions. This function
    attempts the most common options before giving up.
    """

    import nbtlib

    for attr in ("parse_nbt", "parse", "parse_tag"):
        parser = getattr(nbtlib, attr, None)
        if parser:
            return parser(snbt)

    if hasattr(nbtlib, "File") and hasattr(nbtlib.File, "from_snbt"):
        return nbtlib.File.from_snbt(snbt).root

    raise RuntimeError("Unable to parse SNBT with nbtlib")


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


def build_chunked_lines(
    root_tag,
    storage: str,
    target_path: str,
    source: Path | None = None,
    announce: bool = False,
) -> List[str]:
    """Write the payload in multiple commands to avoid overlong lines."""

    try:
        from nbtlib.tag import List as NbtList
    except Exception:  # pragma: no cover - runtime import
        NbtList = None

    lines: List[str] = []
    if source:
        lines.append(f"# Generated from {source}")
    lines.append("# To verify the write, run: data get storage " f"{storage} {target_path}")
    lines.append(f"data modify storage {storage} {target_path} set value {{}}")

    for key, value in root_tag.items():
        key_path = f"{target_path}.{key}"
        is_list = NbtList is not None and isinstance(value, NbtList)

        if is_list:
            lines.append(f"data modify storage {storage} {key_path} set value []")
            for entry in value:
                lines.append(
                    f"data modify storage {storage} {key_path} append value {entry.snbt()}"
                )
        else:
            lines.append(
                f"data modify storage {storage} {key_path} set value {value.snbt()}"
            )

    if announce:
        lines.append(
            'tellraw @s {"text":"Storage write completed","color":"green"}'
        )

    return lines


def build_block_state(palette_entry) -> str:
    """Turn a palette entry into a blockstate string."""

    def unwrap(value):
        return value.value if hasattr(value, "value") else value

    name = unwrap(palette_entry["Name"])
    props = palette_entry.get("Properties")
    if not props:
        return name

    parts: list[str] = []
    for key, value in props.items():
        raw = unwrap(value)
        parts.append(f"{key}={raw}")

    return f"{name}[{','.join(parts)}]"


def _unwrap(value):
    return value.value if hasattr(value, "value") else value


def _build_block_records(root_tag, include_air: bool, offset: tuple[int, int, int]):
    """Return normalized block records from a structure-like tag."""

    palette = [build_block_state(entry) for entry in root_tag.get("palette", [])]
    blocks = root_tag.get("blocks", [])

    normalized: list[tuple[int, int, int, str, str]] = []
    for block in blocks:
        state_idx = int(_unwrap(block.get("state", 0)))
        try:
            block_state = palette[state_idx]
        except IndexError:
            continue

        if not include_air and block_state == "minecraft:air":
            continue

        pos = block.get("pos", [])
        if len(pos) != 3:
            continue

        try:
            x, y, z = (int(_unwrap(p)) + delta for p, delta in zip(pos, offset))
        except Exception:
            continue

        nbt = block.get("nbt")
        nbt_suffix = ""
        if nbt is not None:
            formatter = getattr(nbt, "snbt", None)
            nbt_suffix = formatter() if formatter else str(nbt)

        normalized.append((x, y, z, block_state, nbt_suffix))

    return normalized


def build_setblock_lines(
    root_tag,
    source: Path | None = None,
    announce: bool = False,
    include_air: bool = False,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> List[str]:
    """Create a `.mcfunction` that places every block via `setblock`."""

    records = _build_block_records(root_tag, include_air, offset)

    lines: List[str] = []
    if source:
        lines.append(f"# Generated from {source}")
    lines.append("# Places the structure relative to the current executor position")

    for x, y, z, block_state, nbt_suffix in records:
        lines.append(
            f"setblock ~{x} ~{y} ~{z} {block_state}{nbt_suffix} replace"
        )

    if announce:
        lines.append(
            'tellraw @s {"text":"Structure placement completed","color":"green"}'
        )

    return lines


def build_fill_lines(
    root_tag,
    source: Path | None = None,
    announce: bool = False,
    include_air: bool = False,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> List[str]:
    """Create `.mcfunction` contents using `fill` runs grouped by rows."""

    records = _build_block_records(root_tag, include_air, offset)

    by_state: dict[str, dict[tuple[int, int], list[int]]] = {}
    singles: list[tuple[int, int, int, str, str]] = []

    for x, y, z, state, nbt in records:
        if nbt:
            singles.append((x, y, z, state, nbt))
            continue
        row_key = (y, z)
        rows = by_state.setdefault(state, {})
        rows.setdefault(row_key, []).append(x)

    lines: List[str] = []
    if source:
        lines.append(f"# Generated from {source}")
    lines.append("# Places the structure relative to the current executor position")

    # Emit grouped fills for rows of identical block state
    for state, rows in by_state.items():
        for (y, z), xs in rows.items():
            for start, end in _compress_intervals(xs):
                if start == end:
                    lines.append(f"setblock ~{start} ~{y} ~{z} {state} replace")
                else:
                    lines.append(
                        f"fill ~{start} ~{y} ~{z} ~{end} ~{y} ~{z} {state} replace"
                    )

    # Emit nbt-bearing blocks individually so their data stays intact
    for x, y, z, state, nbt in singles:
        lines.append(f"setblock ~{x} ~{y} ~{z} {state}{nbt} replace")

    if announce:
        lines.append(
            'tellraw @s {"text":"Structure placement completed","color":"green"}'
        )

    return lines


def _compress_intervals(values: list[int]) -> list[tuple[int, int]]:
    """Turn a list of integers into contiguous intervals."""

    if not values:
        return []

    intervals: list[tuple[int, int]] = []
    for x in sorted(values):
        if not intervals or x > intervals[-1][1] + 1:
            intervals.append((x, x))
        else:
            start, end = intervals[-1]
            intervals[-1] = (start, x)
    return intervals


def convert_file(
    input_path: Path,
    output_path: Path,
    storage: str = "convertnbt:data",
    target_path: str = "data",
    announce: bool = False,
    chunk: bool | None = None,
    mode: str = "storage",
    include_air: bool = False,
    center: bool = False,
    use_fill: bool = False,
) -> Iterable[str]:
    """Convert an input NBT/SNBT file into `.mcfunction` contents.

    The output is written to ``output_path`` and also returned as an iterable of
    lines. This enables both library-style use and CLI invocation.

    If ``chunk`` is truthy (or left as ``None`` and the SNBT exceeds 30k
    characters), the function emits many `data modify ... append` commands to
    avoid a single gigantic line that can break in-game limits.
    """

    snbt = read_snbt(input_path)

    lines: List[str]
    if mode == "place":
        tag = parse_snbt_tag(snbt)
        offset = (0, 0, 0)
        if center:
            size = getattr(tag, "get", lambda _x, default=None: default)("size") or []
            try:
                ox = -int(_unwrap(size[0]) // 2)
                oy = 0
                oz = -int(_unwrap(size[2]) // 2)
                offset = (ox, oy, oz)
            except Exception:
                offset = (0, 0, 0)

        if use_fill:
            lines = build_fill_lines(
                tag, input_path, announce, include_air, offset
            )
        else:
            lines = build_setblock_lines(
                tag, input_path, announce, include_air, offset
            )
    elif chunk or (chunk is None and len(snbt) > 30000):
        tag = parse_snbt_tag(snbt)
        lines = build_chunked_lines(tag, storage, target_path, input_path, announce)
    else:
        lines = build_mcfunction_lines(
            snbt, storage, target_path, input_path, announce
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an NBT or SNBT file into a `.mcfunction` that either loads the "
            "data into a storage entry or places each block with setblock commands."
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
    parser.add_argument(
        "--chunk",
        action="store_true",
        default=None,
        help=(
            "Write the payload using multiple append commands to avoid a single "
            "massive line (useful for large structures)."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["storage", "place"],
        default="storage",
        help="Choose `storage` to write into data storage or `place` to emit setblock commands.",
    )
    parser.add_argument(
        "--include-air",
        action="store_true",
        help="When using placement mode, also emit commands for air blocks.",
    )
    parser.add_argument(
        "--center",
        action="store_true",
        help="Offset placement so the structure is centered around the executor (x/z).",
    )
    parser.add_argument(
        "--fill",
        action="store_true",
        help="Group identical rows into fill commands instead of per-block setblock lines.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    convert_file(
        args.input,
        args.output,
        args.storage,
        args.target,
        args.announce,
        args.chunk,
        args.mode,
        args.include_air,
        args.center,
        args.fill,
    )


if __name__ == "__main__":
    main()
