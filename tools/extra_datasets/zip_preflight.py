"""Size of the central directory of a remote zip, from the last 64 KB only (one Range request). usage: python zip_preflight.py <url> <size>"""
import struct, sys, urllib.request
url, size = sys.argv[1], int(sys.argv[2])
req = urllib.request.Request(url, headers={"Range": f"bytes={size - 65536}-{size - 1}"})
tail = urllib.request.urlopen(req, timeout=60).read()
i = tail.rfind(b"PK\x05\x06")
_, _, _, _, entries, cd_size, cd_off, _ = struct.unpack("<IHHHHIIH", tail[i : i + 22])
z64 = tail.rfind(b"PK\x06\x06")
if z64 >= 0:
    _, rec, _, _, _, _, entries, _, cd_size, cd_off = struct.unpack("<IQHHIIQQQQ", tail[z64 : z64 + 56])
print(f"fetched {len(tail)} bytes; entries {entries}; central directory {cd_size} bytes at offset {cd_off}; zip64 {z64 >= 0}")
