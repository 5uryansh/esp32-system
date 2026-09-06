
"""Dev helper: view the bitmap returned by /api/spotify/art.

    python preview_art.py art.bin          # ASCII in the terminal
    python preview_art.py art.bin -o a.png # also write a PNG

Not used by the server. Delete it whenever.
"""

import argparse
import math
import sys

SHADES = " .:-=+*#%@"


def load(path: str, size: int | None) -> tuple[list[list[int]], int]:
    data = open(path, "rb").read()
    if size is None:
        # width == height and 8 pixels per byte, so size = sqrt(len * 8)
        size = int(math.isqrt(len(data) * 8))
        if size * size // 8 != len(data):
            sys.exit(
                f"{path} is {len(data)} bytes, which is not a square 1-bit bitmap. "
                "Pass --size."
            )

    row_bytes = size // 8
    expected = row_bytes * size
    if len(data) != expected:
        sys.exit(f"Expected {expected} bytes for {size}x{size}, got {len(data)}.")

    # A set bit means black ink, MSB first.
    pixels = []
    for y in range(size):
        row = data[y * row_bytes : (y + 1) * row_bytes]
        pixels.append(
            [(row[x // 8] >> (7 - x % 8)) & 1 for x in range(size)]
        )
    return pixels, size


def to_ascii(pixels: list[list[int]], size: int, width: int) -> str:
    """Average blocks of pixels into shades so the whole image fits the terminal."""
    step = max(1, size // width)
    # Terminal cells are about twice as tall as wide.
    lines = []
    for y in range(0, size - step * 2 + 1, step * 2):
        line = []
        for x in range(0, size - step + 1, step):
            block = [
                pixels[y + dy][x + dx]
                for dy in range(step * 2)
                for dx in range(step)
            ]
            ink = sum(block) / len(block)
            line.append(SHADES[min(int(ink * len(SHADES)), len(SHADES) - 1)])
        lines.append("".join(line))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="the .bin file from /api/spotify/art")
    parser.add_argument("--size", type=int, help="square size (guessed by default)")
    parser.add_argument("-o", "--out", help="also write a PNG here")
    parser.add_argument("-w", "--width", type=int, default=100, help="ASCII columns")
    args = parser.parse_args()

    pixels, size = load(args.path, args.size)
    print(f"{size}x{size}, {size * size // 8} bytes\n")
    print(to_ascii(pixels, size, args.width))

    if args.out:
        from PIL import Image

        image = Image.new("1", (size, size))
        # Set bit is black ink, so invert back for a normal image.
        image.putdata([0 if p else 1 for row in pixels for p in row])
        image.save(args.out)
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
