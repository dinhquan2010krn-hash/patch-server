#!/usr/bin/env python3
"""Patch the hardcoded key-server domain inside the ThreeOneOSFive Mach-O binary.

Original host in __cstring:
    mduyk-key-server.onrender.com     (29 bytes)

Two modes:
  1) Render service name (exactly 16 chars -> 29-byte host, byte-identical replacement):
       python tools/patch_domain.py <binary> mduyk-key-srv001 <output>
  2) Arbitrary domain (padded with NUL if shorter than 29 bytes):
       python tools/patch_domain.py <binary> --domain user.pythonanywhere.com <output>
"""
import argparse
import sys
from pathlib import Path

OLD_HOST = b"mduyk-key-server.onrender.com"


def main():
    ap = argparse.ArgumentParser(description="Patch hardcoded server domain in the app binary")
    ap.add_argument("binary", help="path to the original Mach-O binary")
    ap.add_argument("target", help="16-char Render service name, or the full domain with --domain")
    ap.add_argument("output", help="path for the patched binary")
    ap.add_argument("--domain", action="store_true",
                    help="treat TARGET as a full domain (pads with NUL if shorter than 29 bytes)")
    args = ap.parse_args()

    if args.domain:
        host = args.target.strip().lower().encode("ascii", "ignore")
        if len(host) > len(OLD_HOST):
            print(
                f"ERROR: domain too long ({len(host)} > {len(OLD_HOST)} bytes): {host.decode()}\n"
                "       Use a shorter username or the Render mode.",
                file=sys.stderr,
            )
            return 1
        padded = host + b"\x00" * (len(OLD_HOST) - len(host))
        print(f"NOTE: domain padded with {len(OLD_HOST) - len(host)} NUL byte(s) "
              "to keep the original string slot length.")
        new_host = padded
    else:
        name = args.target.strip().lower()
        if len(name) != 16:
            print(f"ERROR: service name must be exactly 16 chars, got {len(name)}: {name!r}",
                  file=sys.stderr)
            return 1
        new_host = (name + ".onrender.com").encode("ascii")
        if len(new_host) != len(OLD_HOST):
            print("ERROR: unexpected host length", file=sys.stderr)
            return 1

    src = Path(args.binary)
    if not src.is_file():
        print(f"ERROR: not found: {src}", file=sys.stderr)
        return 1

    data = src.read_bytes()
    count = data.count(OLD_HOST)
    if count == 0:
        print("ERROR: old domain not found in binary (already patched?)", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data.replace(OLD_HOST, new_host))

    print(f"Replaced {count} occurrence(s): {OLD_HOST.decode()} -> {new_host.split(chr(0).encode())[0].decode()}")
    print(f"Written: {out}")
    print(f"Size: {out.stat().st_size} bytes")
    return 0


def verify(path):
    data = Path(path).read_bytes()
    print("old host occurrences:", data.count(OLD_HOST))
    hosts = set()
    for line in data.split(b"\x00"):
        if b"//" in line and b"mduyk" in line.lower():
            hosts.add(line.split(b"//", 1)[1].split(b"/", 1)[0])
    for host in sorted(hosts):
        print("found host:", host.decode(errors="replace"))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--verify":
        verify(sys.argv[2])
    else:
        raise SystemExit(main())
