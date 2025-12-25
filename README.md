
# Kaleido Stitch (starter app)

A tiny, hackable generator for **kaleidoscopic cross-stitch charts**:

- **35×35 stitches**
- **perfect 8-way symmetry (D8)**
- **7 colors per palette (index 0 = background)**
- outputs **PNG charts + CSV + printable PDF** as a ZIP.

## Run the web app

1) Install deps:

```bash
pip install flask pillow numpy reportlab
```

2) Start:

```bash
python app.py
```

Open: http://127.0.0.1:5000

## Run from CLI

```bash
python generate.py --design rings_spokes --palette jewel_bazaar --seed 123 --out out
```

## Where to edit stuff

- Add/adjust palettes in `kaleido.py` → `PALETTES`
- Add new designs in `kaleido.py` → `DESIGNS`
  - Any design must return indices `0..6` (0 should be background-ish)
  - D8 symmetry is guaranteed by the folding step; your design function only needs to define one octant.

Have fun. Make weird little quilts for the soul. :)
