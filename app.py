
import base64
import io
from datetime import datetime

from flask import Flask, jsonify, request, render_template_string
import kaleido

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kaleido Stitch</title>
  <style>
    :root{
      --bg: #0b0f14;
      --panel: rgba(255,255,255,0.06);
      --panel2: rgba(255,255,255,0.10);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.70);
      --stroke: rgba(255,255,255,0.14);
      --accent: #7dd3fc;
      --accent2: #a78bfa;
    }
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      background: radial-gradient(1200px 800px at 20% 0%, rgba(167,139,250,0.18), transparent 55%),
                  radial-gradient(900px 700px at 90% 10%, rgba(125,211,252,0.16), transparent 55%),
                  var(--bg);
      color: var(--text);
    }
    .wrap{ max-width: 980px; margin: 0 auto; padding: 18px 16px 40px; }
    h1{ margin: 10px 0 6px; font-size: 22px; letter-spacing: 0.2px; }
    p{ margin: 0 0 14px; color: var(--muted); line-height: 1.35; }

    .grid{
      display:grid;
      grid-template-columns: 360px 1fr;
      gap: 14px;
    }
    @media (max-width: 860px){
      .grid{ grid-template-columns: 1fr; }
    }

    .card{
      background: var(--panel);
      border: 1px solid var(--stroke);
      border-radius: 14px;
      padding: 14px;
      backdrop-filter: blur(6px);
    }

    label{ display:block; font-size: 12px; color: var(--muted); margin: 10px 0 6px; }
    select, input[type="number"], input[type="range"]{
      width: 100%;
      box-sizing: border-box;
      background: var(--panel2);
      color: var(--text);
      border: 1px solid var(--stroke);
      border-radius: 10px;
      padding: 10px 10px;
      font-size: 14px;
      outline: none;
    }
    input[type="range"]{ padding: 10px 0; }
    .row{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    @media (max-width: 420px){
      .row{ grid-template-columns: 1fr; }
    }

    button{
      margin-top: 12px;
      width: 100%;
      border: 0;
      border-radius: 12px;
      padding: 12px 12px;
      font-size: 15px;
      font-weight: 650;
      color: #061019;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      cursor: pointer;
    }
    button:active{ transform: translateY(1px); }

    .meta{ margin-top: 10px; font-size: 12px; color: var(--muted); }
    .chips{ display:flex; flex-wrap:wrap; gap: 8px; margin-top: 10px; }
    .chip{
      border: 1px solid var(--stroke);
      border-radius: 999px;
      padding: 6px 10px;
      background: rgba(0,0,0,0.16);
      font-size: 12px;
      color: var(--muted);
    }

    .preview{
      display:flex;
      flex-direction: column;
      gap: 12px;
      align-items: center;
      justify-content: center;
      min-height: 420px;
    }
    .imgbox{
      width: 100%;
      display:flex;
      align-items:center;
      justify-content:center;
      background: rgba(0,0,0,0.20);
      border: 1px dashed var(--stroke);
      border-radius: 14px;
      padding: 12px;
      overflow:hidden;
    }
    img{ max-width: 100%; height:auto; border-radius: 10px; image-rendering: pixelated; }
    .actions{ display:flex; gap: 10px; width:100%; justify-content:center; flex-wrap:wrap; }
    .linkbtn{
      display:inline-block;
      text-decoration:none;
      border: 1px solid var(--stroke);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(255,255,255,0.06);
      color: var(--text);
      font-weight: 600;
      font-size: 14px;
    }
    .hint{ font-size: 12px; color: var(--muted); text-align:center; }
  </style>
</head>

<body>
  <div class="wrap">
    <h1>Kaleido Stitch</h1>
    <p>35×35, perfect 8-way symmetry, up to 7 colors. Generate an image you can long-press on your phone to save.</p>

    <div class="grid">
      <div class="card">
        <form id="form">
          <label>Design</label>
          <select name="design">
            {% for k, v in designs.items() %}
              <option value="{{k}}">{{v}}</option>
            {% endfor %}
          </select>

          <label>Palette</label>
          <select name="palette">
            {% for k, v in palettes.items() %}
              <option value="{{k}}">{{v}}</option>
            {% endfor %}
          </select>

          <div class="row">
            <div>
              <label>Seed (0 = random)</label>
              <input type="number" name="seed" value="0" min="0" step="1">
            </div>
            <div>
              <label># Colors (3–7)</label>
              <input type="number" name="ncolors" value="7" min="3" max="7" step="1">
            </div>
          </div>

          <label>Contiguity (smoother blocks)</label>
          <input type="range" name="smooth" min="0" max="6" value="3">

          <label>Line bias (more unbroken lines)</label>
          <input type="range" name="lines" min="0" max="10" value="6">

          <div class="row">
            <div>
              <label>Cell size (px)</label>
              <input type="number" name="cell" value="22" min="10" max="64" step="1">
            </div>
            <div>
              <label>Gridline (px)</label>
              <input type="number" name="gridline" value="1" min="0" max="4" step="1">
            </div>
          </div>

          <button type="submit">Generate image</button>
          <div class="meta" id="status">Ready.</div>
          <div class="chips" id="chips"></div>
        </form>
      </div>

      <div class="card preview">
        <div class="imgbox">
          <img id="out" alt="Generated cross stitch chart preview" />
        </div>
        <div class="actions">
          <a class="linkbtn" id="download" href="#" download="kaleido.png" style="display:none">Download PNG</a>
        </div>
        <div class="hint">Tip: on iPhone you can also long-press the image → “Save to Photos”.</div>
      </div>
    </div>
  </div>

<script>
  const form = document.getElementById('form');
  const out = document.getElementById('out');
  const statusEl = document.getElementById('status');
  const chips = document.getElementById('chips');
  const download = document.getElementById('download');

  function setStatus(t){ statusEl.textContent = t; }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    chips.innerHTML = "";
    download.style.display = "none";
    setStatus("Generating…");

    const fd = new FormData(form);
    const resp = await fetch("/api/generate", { method: "POST", body: fd });
    if (!resp.ok){
      setStatus("Oops — generation failed.");
      return;
    }
    const data = await resp.json();

    out.src = data.png_data_url;
    download.href = data.png_data_url;
    download.download = data.filename || "kaleido.png";
    download.style.display = "inline-block";

    setStatus(data.caption || "Done.");

    (data.used_colors || []).forEach((hex, i) => {
      const c = document.createElement("div");
      c.className = "chip";
      c.textContent = `#${i}: ${hex}`;
      c.style.borderColor = hex;
      chips.appendChild(c);
    });
  });
</script>
</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(
        PAGE,
        designs=kaleido.DESIGN_LABELS,
        palettes=kaleido.PALETTE_LABELS,
    )

@app.post("/api/generate")
def api_generate():
    design = request.form.get("design", "rosette_lines")
    palette = request.form.get("palette", "jewel_bazaar")
    seed = int(request.form.get("seed", "0") or "0")
    ncolors = int(request.form.get("ncolors", "7") or "7")
    smooth = int(request.form.get("smooth", "3") or "3")
    lines = int(request.form.get("lines", "6") or "6")
    cell = int(request.form.get("cell", "22") or "22")
    gridline = int(request.form.get("gridline", "1") or "1")

    if ncolors < 3: ncolors = 3
    if ncolors > 7: ncolors = 7
    if smooth < 0: smooth = 0
    if smooth > 6: smooth = 6
    if lines < 0: lines = 0
    if lines > 10: lines = 10

    if seed == 0:
      # deterministic-enough per request, but still “random” for users
      seed = int(datetime.now().strftime("%H%M%S%f")) % 2_000_000_000

    png_bytes, used_colors = kaleido.generate_png_preview(
        design=design,
        palette=palette,
        seed=seed,
        ncolors=ncolors,
        smooth=smooth,
        lines=lines,
        cell=cell,
        gridline=gridline,
    )

    b64 = base64.b64encode(png_bytes).decode("ascii")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"kaleido_{design}_{palette}_seed{seed}_{stamp}.png"

    return jsonify({
        "png_data_url": "data:image/png;base64," + b64,
        "used_colors": used_colors,
        "filename": fname,
        "caption": f"{design} • {palette} • seed {seed} • {ncolors} colors",
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
