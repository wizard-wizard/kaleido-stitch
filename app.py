
from __future__ import annotations

import io, os
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

import kaleido

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Kaleido Stitch</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 28px; max-width: 920px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 16px; }
    label { display:block; font-weight: 600; margin-top: 10px; }
    select, input { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #ccc; }
    button { margin-top: 14px; padding: 12px 14px; border-radius: 10px; border: 0; background: #222; color: #fff; font-weight: 700; cursor: pointer; }
    button:hover { opacity: 0.92; }
    .small { color:#444; font-size: 0.95rem; line-height: 1.35; }
    code { background: #f6f6f6; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>Kaleido Stitch</h1>
  <p class="small">Generate a 35×35 cross-stitch chart with perfect 8-way kaleidoscopic symmetry (D8). Output is a ZIP with PNGs + CSV + printable PDF.</p>

  <div class="row">
    <div class="card">
      <form action="/generate" method="post">
        <label>Design</label>
        <select name="design">
          {% for k in designs %}
            <option value="{{k}}">{{k}}</option>
          {% endfor %}
        </select>

        <label>Palette</label>
        <select name="palette">
          {% for k in palettes %}
            <option value="{{k}}">{{k}}</option>
          {% endfor %}
        </select>

        <label>Seed (changes the variation)</label>
        <input name="seed" type="number" value="0" min="0" max="999999" />

        <label>Chart cell size (pixels)</label>
        <input name="cell" type="number" value="22" min="10" max="60" />

        <label>Gridline thickness</label>
        <input name="gridline" type="number" value="1" min="0" max="4" />

        <button type="submit">Generate ZIP</button>
      </form>
    </div>

    <div class="card">
      <h3>Tips</h3>
      <ul class="small">
        <li>If you like a pattern, keep its <code>seed</code> so you can regenerate it later.</li>
        <li>Set gridline to <code>0</code> if you want a clean chart image without the gray grid border.</li>
        <li>Want more palettes/designs? Add them in <code>kaleido.py</code> — it’s intentionally hackable.</li>
      </ul>
      <h3>CLI</h3>
      <p class="small">You can also generate from the command line:</p>
      <pre class="small"><code>python generate.py --design rings_spokes --palette jewel_bazaar --seed 123 --out out</code></pre>
    </div>
  </div>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(
        TEMPLATE,
        designs=sorted(kaleido.DESIGNS.keys()),
        palettes=sorted(kaleido.PALETTES.keys()),
    )

@app.post("/generate")
def generate():
    design = request.form.get("design", "rings_spokes")
    palette = request.form.get("palette", "jewel_bazaar")
    seed = int(request.form.get("seed", "0") or "0")
    cell = int(request.form.get("cell", "22") or "22")
    gridline = int(request.form.get("gridline", "1") or "1")

    zbytes = kaleido.generate_bundle(design, palette, seed=seed, cell=cell, gridline=gridline)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"kaleido_{design}_{palette}_seed{seed}_{stamp}.zip"
    return send_file(
        io.BytesIO(zbytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=fname,
    )

if __name__ == "__main__":
    # default: http://127.0.0.1:5000
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
