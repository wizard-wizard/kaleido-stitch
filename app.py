
from __future__ import annotations

import io, os, uuid, zipfile
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

import kaleido

app = Flask(__name__)

GENERATED_DIR = os.path.join(app.root_path, "static", "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

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

    # Extract PNGs from the in-memory ZIP and save them so the browser can display them
    token = uuid.uuid4().hex
    preview_name = f"{token}_preview.png"
    chart_name = f"{token}_chart.png"
    preview_path = os.path.join(GENERATED_DIR, preview_name)
    chart_path = os.path.join(GENERATED_DIR, chart_name)

    with zipfile.ZipFile(io.BytesIO(zbytes), "r") as z:
        # Find likely image files in the bundle
        names = z.namelist()
        preview_candidates = [n for n in names if n.lower().endswith(".png") and "preview" in n.lower()]
        chart_candidates = [n for n in names if n.lower().endswith(".png") and ("chart" in n.lower() or "grid" in n.lower())]

        if not preview_candidates:
            # fallback: any png
            preview_candidates = [n for n in names if n.lower().endswith(".png")]

        if not preview_candidates:
            return "No PNGs found in bundle ZIP.", 500

        preview_src = preview_candidates[0]
        chart_src = chart_candidates[0] if chart_candidates else preview_src

        with z.open(preview_src) as f:
            with open(preview_path, "wb") as out:
                out.write(f.read())

        with z.open(chart_src) as f:
            with open(chart_path, "wb") as out:
                out.write(f.read())

    preview_url = f"/static/generated/{preview_name}"
    chart_url = f"/static/generated/{chart_name}"

    return render_template_string("""
    <!doctype html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Kaleido Stitch — Result</title>
        <style>
          body { font-family: system-ui, sans-serif; padding: 16px; }
          img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 12px; }
          .hint { color: #555; margin: 6px 0 14px; }
          a.button {
            display: inline-block; padding: 10px 14px; border: 1px solid #333;
            border-radius: 10px; text-decoration: none; color: #111; margin-right: 10px;
          }
          .block { margin-bottom: 22px; }
        </style>
      </head>
      <body>
        <h2>Your design</h2>
        <div class="hint">iPhone tip: press and hold the image → “Save to Photos”.</div>

        <div class="block">
          <h3>Preview (easy to save)</h3>
          <img src="{{ preview_url }}?v={{ token }}" alt="Preview">
          <p><a class="button" href="{{ preview_url }}" target="_blank">Open preview</a></p>
        </div>

        <div class="block">
          <h3>Chart (with grid)</h3>
          <img src="{{ chart_url }}?v={{ token }}" alt="Chart">
          <p><a class="button" href="{{ chart_url }}" target="_blank">Open chart</a></p>
        </div>

        <p><a class="button" href="/">Make another</a></p>
      </body>
    </html>
    """, preview_url=preview_url, chart_url=chart_url, token=token)
if __name__ == "__main__":
    # default: http://127.0.0.1:5000
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
