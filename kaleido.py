
"""
Kaleido Stitch — kaleidoscopic 35×35 cross-stitch chart generator (D8 symmetry).

- Fixed size: 35×35
- Perfect 8-way (D8) symmetry via octant folding
- 7-color palettes (index 0 = background)

This module provides:
- design functions -> 35×35 index grid
- palettes
- renderers for chart/preview/legend
- a helper that returns a ZIP bundle (PNG + CSV + PDF)

MIT-ish: do whatever you want; credit appreciated but not required.
"""
from __future__ import annotations

import io, math, random, csv, zipfile
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

N = 35
CX = CY = N // 2  # 17

def fold_d8(dx: int, dy: int) -> Tuple[int, int]:
    """
    Fold (dx,dy) into the fundamental octant for D8 symmetry:
    - reflect across x/y axes (abs)
    - reflect across diagonal y=x (ensure dy <= dx)
    """
    dx, dy = abs(dx), abs(dy)
    if dy > dx:
        dx, dy = dy, dx
    return dx, dy

def make_pattern_octant(func: Callable[[int, int], int]) -> np.ndarray:
    """
    Build a full N×N grid by folding each coordinate into an octant and calling func(fx,fy).
    """
    grid = np.zeros((N, N), dtype=np.int32)
    for y in range(N):
        for x in range(N):
            dx, dy = x - CX, y - CY
            fx, fy = fold_d8(dx, dy)
            grid[y, x] = int(func(fx, fy))
    return grid

def quantize(val: float, thresholds: List[float]) -> int:
    """
    thresholds ascending; returns bin index 0..len(thresholds)
    """
    for i, t in enumerate(thresholds):
        if val < t:
            return i
    return len(thresholds)

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# -------------------------
# Palettes (7 colors each)
# index 0 = background
# -------------------------
PALETTES: Dict[str, List[str]] = {
    "jewel_bazaar": ["#F7F0E8", "#1B4F72", "#7D3C98", "#117A65", "#B03A2E", "#AF601A", "#5D4037"],
    "forest_copper": ["#FBF6EF", "#1E2D24", "#2E6B4F", "#7A8F3A", "#B76E3A", "#6B3E26", "#2A7FAA"],
    "ocean_coral":  ["#F5FBFF", "#0B3954", "#087E8B", "#BFD7EA", "#FF5A5F", "#C81D25", "#4E8098"],
    "night_neon":   ["#0A0A0B", "#00E5FF", "#FF2EEA", "#FFD400", "#00FF6A", "#7C4DFF", "#FFFFFF"],
    "antique_sampler":["#FAF5EA","#2E2A24","#6C4B3B","#A77B5A","#C2A46B","#6E7F63","#9B4F4F"],
}

# -------------------------
# Designs (each returns 0..6)
# -------------------------
def _edge_mask(fx: int, fy: int, maxd: int = 16) -> bool:
    # Keep a clean, centered diamond-ish boundary.
    return max(fx, fy) <= maxd

def design_rings_spokes(seed: int = 0) -> np.ndarray:
    rng = random.Random(seed)
    k_r = rng.uniform(0.55, 0.9)
    k_a = rng.uniform(4.5, 7.0)
    wob = rng.uniform(0.15, 0.35)
    thresholds = [-0.55, -0.25, -0.05, 0.10, 0.28, 0.52]  # 7 bins
    def f(fx: int, fy: int) -> int:
        if not _edge_mask(fx, fy): return 0
        r = math.sqrt(fx*fx + fy*fy) + 1e-6
        a = math.atan2(fy, fx + 1e-6)
        val = math.sin(r*k_r) * 0.65 + math.cos(a*k_a) * 0.55 + math.sin((fx-fy)*0.7) * wob
        return quantize(val, thresholds)
    return make_pattern_octant(f)

def design_petal_vault(seed: int = 0) -> np.ndarray:
    rng = random.Random(seed)
    k1 = rng.uniform(0.35, 0.55)
    k2 = rng.uniform(1.2, 1.8)
    thresholds = [-0.4, -0.15, 0.05, 0.20, 0.38, 0.60]
    def f(fx: int, fy: int) -> int:
        if not _edge_mask(fx, fy): return 0
        r = math.sqrt(fx*fx + fy*fy) + 1e-6
        a = math.atan2(fy, fx + 1e-6)
        val = math.cos(r*k1) * (0.65 + 0.35*math.cos(a*8)) + 0.35*math.sin((fx+fy)*k2)
        if r < 2.2:
            val += 0.7
        return quantize(val, thresholds)
    return make_pattern_octant(f)

def design_starburst(seed: int = 0) -> np.ndarray:
    rng = random.Random(seed)
    k = rng.uniform(0.85, 1.15)
    thresholds = [-0.45, -0.2, 0.0, 0.18, 0.35, 0.55]
    def f(fx: int, fy: int) -> int:
        if not _edge_mask(fx, fy): return 0
        r = math.sqrt(fx*fx + fy*fy) + 1e-6
        a = math.atan2(fy, fx + 1e-6)
        val = (math.cos(a*12) * 0.7 + math.cos(r*k) * 0.6 + math.sin((fx-fy)*0.9) * 0.25)
        if fy == 0 or fx == fy:
            val += 0.35
        return quantize(val, thresholds)
    return make_pattern_octant(f)

def design_mosaic_steps(seed: int = 0) -> np.ndarray:
    thresholds = [0.6, 1.15, 1.7, 2.2, 2.8, 3.4]
    def f(fx: int, fy: int) -> int:
        if not _edge_mask(fx, fy): return 0
        v = 0.0
        v += 1.1 if ((fx+fy) % 4 in (0,1)) else 0.0
        v += 1.0 if ((fx-fy) % 5 in (0,1)) else 0.0
        v += 0.9 if (fx % 3 == 0 or fy % 3 == 0) else 0.0
        r = int(math.sqrt(fx*fx + fy*fy))
        v += (r % 6) * 0.35
        v += 0.8 if ((fx*fy) % 11 == 0) else 0.0
        return quantize(v, thresholds)
    return make_pattern_octant(f)

def design_knotwork(seed: int = 0) -> np.ndarray:
    thresholds = [0.7, 1.35, 2.0, 2.55, 3.2, 3.9]
    def f(fx: int, fy: int) -> int:
        if not _edge_mask(fx, fy): return 0
        v = 0.0
        v += 1.8 if (fx % 4 in (1,2)) and (fy % 6 in (2,3)) else 0.0
        v += 1.6 if (fy % 4 in (1,2)) and (fx % 6 in (2,3)) else 0.0
        r = math.sqrt(fx*fx + fy*fy)
        v += 1.5 if int(r) % 5 == 0 else 0.0
        v += 0.8 if (fx % 7 == 0 and fy % 7 == 0) else 0.0
        v += 0.6*(math.sin((fx+1)*0.8) + math.cos((fy+1)*0.7))
        return quantize(v, thresholds)
    return make_pattern_octant(f)

def design_lattice_garden(seed: int = 0) -> np.ndarray:
    thresholds = [-0.4, -0.15, 0.05, 0.22, 0.40, 0.62]
    def f(fx: int, fy: int) -> int:
        if not _edge_mask(fx, fy): return 0
        r = math.sqrt(fx*fx + fy*fy) + 1e-6
        val = 0.45*math.sin(fx*0.9) + 0.45*math.cos(fy*1.05) + 0.55*math.cos(r*0.55)
        val += 0.25*math.cos((fx-fy)*1.7)
        return quantize(val, thresholds)
    return make_pattern_octant(f)

DESIGNS: Dict[str, Callable[[int], np.ndarray]] = {
    "rings_spokes": design_rings_spokes,
    "petal_vault": design_petal_vault,
    "starburst": design_starburst,
    "mosaic_steps": design_mosaic_steps,
    "knotwork": design_knotwork,
    "lattice_garden": design_lattice_garden,
}

# -------------------------
# Rendering
# -------------------------
def render_chart(grid: np.ndarray, palette: List[str], cell: int = 22, gridline: int = 1) -> Image.Image:
    h, w = grid.shape
    img = Image.new("RGB", (w*cell + (w+1)*gridline, h*cell + (h+1)*gridline), (230,230,230))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            c = hex_to_rgb(palette[int(grid[y, x])])
            x0 = x*cell + (x+1)*gridline
            y0 = y*cell + (y+1)*gridline
            draw.rectangle([x0, y0, x0+cell-1, y0+cell-1], fill=c)
    return img

def render_preview(grid: np.ndarray, palette: List[str], cell: int = 12) -> Image.Image:
    h, w = grid.shape
    img = Image.new("RGB", (w*cell, h*cell), hex_to_rgb(palette[0]))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            c = hex_to_rgb(palette[int(grid[y, x])])
            x0, y0 = x*cell, y*cell
            draw.rectangle([x0, y0, x0+cell-1, y0+cell-1], fill=c)
    return img

def render_legend(palette: List[str], title: str) -> Image.Image:
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    sw, pad = 44, 14
    rows = len(palette)
    w = 760
    h = pad*2 + 40 + rows*(sw+10)
    img = Image.new("RGB", (w, h), (255,255,255))
    draw = ImageDraw.Draw(img)
    draw.text((pad, pad), title, fill=(20,20,20), font=font)
    y = pad + 40
    for i, hx in enumerate(palette):
        draw.rectangle([pad, y, pad+sw, y+sw], fill=hex_to_rgb(hx), outline=(0,0,0))
        draw.text((pad+sw+14, y+10), f"{i}: {hx}", fill=(20,20,20), font=font_small)
        y += sw+10
    return img

def grid_to_csv_bytes(grid: np.ndarray) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["y\\x"] + list(range(grid.shape[1])))
    for y in range(grid.shape[0]):
        w.writerow([y] + list(map(int, grid[y])))
    return buf.getvalue().encode("utf-8")

def palette_to_csv_bytes(palette: List[str]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["index", "hex"])
    for i, hx in enumerate(palette):
        w.writerow([i, hx])
    return buf.getvalue().encode("utf-8")

def build_pdf_bytes(title: str, chart_img: Image.Image, legend_img: Image.Image) -> bytes:
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=landscape(letter))
    pw, ph = landscape(letter)
    m = 36
    c.setFont("Helvetica-Bold", 18)
    c.drawString(m, ph - m, title)
    top_y = ph - m - 24
    left_w = pw * 0.62
    right_w = pw - left_w - 2*m

    # Chart
    chart_reader = ImageReader(chart_img)
    cw, ch = chart_img.size
    chart_max_w = left_w - m
    chart_max_h = top_y - m
    scale = min(chart_max_w / cw, chart_max_h / ch)
    c.drawImage(chart_reader, m, m, width=cw*scale, height=ch*scale, preserveAspectRatio=True, mask='auto')

    # Legend
    legend_reader = ImageReader(legend_img)
    lw, lh = legend_img.size
    leg_max_w = right_w
    leg_max_h = top_y - m
    lscale = min(leg_max_w / lw, leg_max_h / lh)
    lx = left_w
    c.drawImage(legend_reader, lx, top_y - lh*lscale, width=lw*lscale, height=lh*lscale, preserveAspectRatio=True, mask='auto')

    c.setFont("Helvetica", 10)
    c.drawString(m, 14, "35×35 stitches • perfect 8-way symmetry (D8) • 7 colors incl. background (index 0)")
    c.showPage()
    c.save()
    return pdf_buf.getvalue()

def generate_bundle(design_key: str, palette_key: str, seed: int = 0, cell: int = 22, gridline: int = 1) -> bytes:
    if design_key not in DESIGNS:
        raise KeyError(f"Unknown design_key: {design_key}. Options: {sorted(DESIGNS)}")
    if palette_key not in PALETTES:
        raise KeyError(f"Unknown palette_key: {palette_key}. Options: {sorted(PALETTES)}")

    grid = DESIGNS[design_key](seed)
    palette = PALETTES[palette_key]

    chart = render_chart(grid, palette, cell=cell, gridline=gridline)
    preview = render_preview(grid, palette, cell=max(6, cell//2))
    legend = render_legend(palette, f"{design_key} — {palette_key} (35×35, 7 colors incl. background)")
    pdf = build_pdf_bytes(f"{design_key} — {palette_key} — seed {seed}", chart, legend)

    # Pack ZIP
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # images
        for name, img in [("chart.png", chart), ("preview.png", preview), ("legend.png", legend)]:
            b = io.BytesIO()
            img.save(b, format="PNG")
            z.writestr(name, b.getvalue())
        z.writestr("pattern_indices.csv", grid_to_csv_bytes(grid))
        z.writestr("palette.csv", palette_to_csv_bytes(palette))
        z.writestr("chart.pdf", pdf)
        z.writestr("README.txt", (
            "Kaleido Stitch bundle\\n\\n"
            "- chart.png: grid + colored blocks\\n"
            "- preview.png: colored blocks, no grid\\n"
            "- legend.png: index->hex list\\n"
            "- pattern_indices.csv: 35×35 indices (0..6)\\n"
            "- palette.csv: index->hex\\n"
            "- chart.pdf: printable chart + legend\\n\\n"
            "Notes:\\n"
            "- index 0 is background\\n"
            "- design is guaranteed D8 (8-way) symmetric\\n"
        ))
    return zbuf.getvalue()
