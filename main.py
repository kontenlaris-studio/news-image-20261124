#!/usr/bin/env python3
"""Publish the 24 November 2026 news poster.

The poster image lives in artwork.png beside this script. This program
checks that it is a well-formed PNG within the bounty limits and then
places an exact copy at /output/entry.png. Standard library only, no
network use, and the result is byte-for-byte identical on every run.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARTWORK = os.path.join(HERE, "artwork.png")
TARGET = "/output/entry.png"
LIMIT_BYTES = 1_048_576
LIMIT_SIDE = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(message):
    print("error: " + message, file=sys.stderr)
    sys.exit(1)


def main():
    try:
        with open(ARTWORK, "rb") as handle:
            image = handle.read()
    except OSError as exc:
        fail("cannot read artwork.png (%s)" % exc)
    if image[:8] != PNG_MAGIC:
        fail("artwork.png is not a PNG image")
    if len(image) > LIMIT_BYTES:
        fail("artwork.png is over the 1 MiB limit")
    if image[12:16] != b"IHDR":
        fail("artwork.png has no IHDR chunk")
    # The last 12 bytes of a PNG are the IEND chunk: length 0, tag IEND, CRC.
    if len(image) < 12 or image[-8:-4] != b"IEND":
        fail("artwork.png has no IEND chunk")
    width, height = struct.unpack(">II", image[16:24])
    if width > LIMIT_SIDE or height > LIMIT_SIDE:
        fail("artwork.png is larger than 1024x1024")
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    with open(TARGET, "wb") as handle:
        handle.write(image)
    print("wrote %s (%d bytes, %dx%d)" % (TARGET, len(image), width, height))


if __name__ == "__main__":
    main()
