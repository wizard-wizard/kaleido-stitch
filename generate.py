
from __future__ import annotations

import argparse, os, io, zipfile
from pathlib import Path

import kaleido

def main():
    p = argparse.ArgumentParser(description="Generate a Kaleido Stitch ZIP bundle.")
    p.add_argument("--design", default="rings_spokes", choices=sorted(kaleido.DESIGNS.keys()))
    p.add_argument("--palette", default="jewel_bazaar", choices=sorted(kaleido.PALETTES.keys()))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cell", type=int, default=22)
    p.add_argument("--gridline", type=int, default=1)
    p.add_argument("--out", default="out", help="Output directory (will be created).")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    zbytes = kaleido.generate_bundle(args.design, args.palette, seed=args.seed, cell=args.cell, gridline=args.gridline)

    zpath = out / f"kaleido_{args.design}_{args.palette}_seed{args.seed}.zip"
    zpath.write_bytes(zbytes)

    # Optional: extract for convenience
    extract_dir = out / f"kaleido_{args.design}_{args.palette}_seed{args.seed}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        z.extractall(extract_dir)

    print(f"Wrote: {zpath}")
    print(f"Extracted to: {extract_dir}")

if __name__ == "__main__":
    main()
