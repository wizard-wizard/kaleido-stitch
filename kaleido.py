import math
import io
import random
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

GRID = 35  # fixed for now

# --- Palettes (index 0 is background). Up to 7 colors total. ---
PALETTES: Dict[str, List[str]] = {
    "jewel_bazaar": ["#0b0f14", "#2dd4bf", "#60a5fa", "#a78bfa", "#fb7185", "#fbbf24", "#34d399"],
    "moth_moon":    ["#0a0c10", "#cbd5e1", "#94a3b8", "#a78bfa", "#38bdf8", "#f472b6", "#fbbf24"],
    "forest_glow":  ["#070b09", "#14532d", "#22c55e", "#a3e635", "#10b981", "#0ea5e9", "#facc15"],
    "embers":       ["#0b0b0f", "#7f1d1d", "#ef4444", "#f97316", "#fbbf24", "#fde68a", "#f43f5e"],
    "sea_glass":    ["#070b10", "#0ea5e9", "#22d3ee", "#34d399", "#a7f3d0", "#c7d2fe", "#f5d0fe"],
    "ink_copper":   ["#07070a", "#e2e8f0", "#94a3b8", "#b45309", "#f59e0b", "#fb7185", "#38bdf8"],
    "sunset_sorbet":["#090a10", "#fb7185", "#f97316", "#fbbf24", "#60a5fa", "#a78bfa", "#34d399"],
    "lichen_stone": ["#0a0e0c", "#e7e5e4", "#a8a29e", "#65a30d", "#84cc16", "#22c55e", "#0ea5e9"],
}

PALETTE_LABELS = {
    "jewel_bazaar": "Jewel Bazaar",
    "moth_moon": "Moth & Moon",
    "forest_glow": "Forest Glow",
    "embers": "Embers",
    "sea_glass": "Sea Glass",
    "ink_copper": "Ink & Copper",
    "sunset_sorbet": "Sunset Sorbet",
    "lichen_stone": "Lichen Stone",
}

# --- Design registry ---
DESIGN_LABELS = {
    "rosette_lines": "Rosette Lines (contiguous + strong bands)",
    "petal_fan": "Petal Fan (soft wedges)",
    "rings_spokes": "Rings + Spokes (classic)",
    "labyrinth": "Labyrinth (chunky paths)",
    "starweave": "Starweave (crisp star geometry)",
    "bloomfield": "Bloomfield (big color fields)",
}

# -----------------------------
# Symmetry + helpers
# -----------------------------

def _d8_fold_from_octant(octant: np.ndarray) -> np.ndarray:
    """
    octant is a square array sized N×N describing one octant-ish wedge.
    We turn it into a full GRID×GRID with perfect D8 symmetry.
    """
    n = octant.shape[0]
    half = GRID // 2 + 1  # 18 for 35
    if n != half:
        raise ValueError(f"octant must be {half}×{half} for GRID={GRID}")

    # Create a quadrant by mirroring across diagonal
    quad = np.minimum(octant, octant.T) * 0 + octant  # keep dtype
    quad = np.triu(quad) + np.triu(quad, 1).T  # mirror across diagonal

    # Mirror to full grid (D4), then add rotations (D8 is covered by diag + mirrors)
    top = np.concatenate([quad[:, :-1], np.fliplr(quad)], axis=1)  # width 35
    full = np.concatenate([top[:-1, :], np.flipud(top)], axis=0)   # height 35
    return full

def _majority_smooth(grid: np.ndarray, k: int, iters: int) -> np.ndarray:
    """
    Simple majority filter that strongly increases contiguous areas.
    """
    if iters <= 0:
        return grid
    g = grid.copy()
    h, w = g.shape
    for _ in range(iters):
        out = g.copy()
        for y in range(h):
            y0, y1 = max(0, y-1), min(h, y+2)
            for x in range(w):
                x0, x1 = max(0, x-1), min(w, x+2)
                patch = g[y0:y1, x0:x1].ravel()
                counts = np.bincount(patch, minlength=k)
                out[y, x] = int(np.argmax(counts))
        g = out
    return g

def _quantize_field(field: np.ndarray, ncolors: int) -> np.ndarray:
    """
    Map a float field to indices 0..ncolors-1 with quantile-ish buckets.
    """
    f = field.copy()
    f = (f - f.min()) / (f.max() - f.min() + 1e-9)
    # Make background slightly more likely
    # (helps negative space + nicer “stitch chart” readability)
    bins = np.linspace(0, 1, ncolors + 1)
    idx = np.digitize(f, bins[1:-1], right=False)
    return idx.astype(np.int32)

def _octant_coords() -> Tuple[np.ndarray, np.ndarray]:
    half = GRID // 2 + 1
    y, x = np.mgrid[0:half, 0:half]
    # normalize to center at (0,0) being the middle of the full grid
    cx = (GRID - 1) / 2.0
    cy = (GRID - 1) / 2.0
    X = (x - cx)
    Y = (y - cy)
    return X, Y

def _design_field(design: str, seed: int, lines: int) -> np.ndarray:
    """
    Produce a smooth-ish scalar field over the octant. 'lines' increases band structure.
    """
    rng = np.random.RandomState(seed)
    X, Y = _octant_coords()

    r = np.sqrt(X*X + Y*Y)
    a = np.arctan2(Y, X + 1e-9)

    # low-frequency “blobs”
    blobs = np.zeros_like(r, dtype=np.float32)
    for _ in range(6):
        cx = rng.uniform(-6, 6)
        cy = rng.uniform(-6, 6)
        s  = rng.uniform(6.0, 14.0)
        blobs += np.exp(-((X-cx)**2 + (Y-cy)**2) / (2*s*s)).astype(np.float32)

    # controllable banding for “unbroken lines”
    band_amp = (lines / 10.0) * 1.15
    bands = (
        0.55*np.sin((r/1.6) + rng.uniform(0, 2*math.pi)) +
        0.45*np.sin((a*6.0) + rng.uniform(0, 2*math.pi))
    ).astype(np.float32)

    if design == "rosette_lines":
        field = 1.15*blobs + band_amp*bands + 0.60*np.cos(a*8.0).astype(np.float32) - 0.10*r.astype(np.float32)

    elif design == "petal_fan":
        field = 1.10*blobs + 0.85*np.cos(a*10.0).astype(np.float32) - 0.10*r.astype(np.float32) + 0.35*band_amp*bands

    elif design == "rings_spokes":
        field = 0.95*blobs + 0.95*np.sin(r/1.4).astype(np.float32) + 0.70*np.cos(a*8.0).astype(np.float32) + 0.35*band_amp*bands

    elif design == "labyrinth":
        # more chunky paths: use abs(sin) “corridors”
        field = 0.65*blobs + 1.10*np.abs(np.sin(r/1.7)).astype(np.float32) + 0.85*np.abs(np.sin(a*6.0)).astype(np.float32) + 0.25*band_amp*bands

    elif design == "starweave":
        field = 0.80*blobs + 1.05*np.cos(a*12.0).astype(np.float32) + 0.80*np.sin(r/1.8).astype(np.float32) + 0.35*band_amp*bands

    elif design == "bloomfield":
        field = 1.60*blobs - 0.12*r.astype(np.float32) + 0.20*band_amp*bands

    else:
        field = blobs + band_amp*bands

    # tiny noise so quantization isn’t too “stuck”
    field += (rng.normal(0, 0.03, size=field.shape)).astype(np.float32)
    return field

def generate_indices(design: str, seed: int, ncolors: int, smooth: int, lines: int) -> np.ndarray:
    half = GRID // 2 + 1
    field = _design_field(design, seed, lines)
    octant = _quantize_field(field, ncolors)
    if smooth > 0:
        octant = _majority_smooth(octant, ncolors, iters=smooth)

    if octant.shape != (half, half):
        octant = octant[:half, :half]

    full = _d8_fold_from_octant(octant)
    # Optional: one more light smoothing on full grid (keeps symmetry)
    if smooth >= 4:
        full = _majority_smooth(full, ncolors, iters=1)
    return full

# -----------------------------
# Rendering
# -----------------------------

def render_png(indices: np.ndarray, palette: List[str], cell: int = 22, gridline: int = 1) -> bytes:
    h, w = indices.shape
    img_w = w * cell + (w+1)*gridline
    img_h = h * cell + (h+1)*gridline
    im = Image.new("RGB", (img_w, img_h), (0,0,0))
    draw = ImageDraw.Draw(im)

    # gridline color (slightly light)
    gl = (40, 46, 56) if gridline > 0 else None
    if gridline > 0:
        draw.rectangle([0,0,img_w,img_h], fill=gl)

    def hex_to_rgb(hx: str):
        hx = hx.lstrip("#")
        return tuple(int(hx[i:i+2], 16) for i in (0,2,4))

    rgb = [hex_to_rgb(c) for c in palette]

    for y in range(h):
        for x in range(w):
            idx = int(indices[y, x])
            color = rgb[idx]
            x0 = gridline + x*(cell+gridline)
            y0 = gridline + y*(cell+gridline)
            draw.rectangle([x0, y0, x0+cell-1, y0+cell-1], fill=color)

    bio = io.BytesIO()
    im.save(bio, format="PNG", optimize=True)
    return bio.getvalue()

def generate_png_preview(
    design: str,
    palette: str,
    seed: int,
    ncolors: int = 7,
    smooth: int = 3,
    lines: int = 6,
    cell: int = 22,
    gridline: int = 1,
) -> Tuple[bytes, List[str]]:
    if design not in DESIGN_LABELS:
        design = "rosette_lines"
    if palette not in PALETTES:
        palette = "jewel_bazaar"

    pal = PALETTES[palette][:ncolors]
    indices = generate_indices(design=design, seed=seed, ncolors=ncolors, smooth=smooth, lines=lines)
    png = render_png(indices, pal, cell=cell, gridline=gridline)

    used = []
    # return the actual palette entries (index order) for UI chips
    for c in pal:
        used.append(c)
    return png, used
