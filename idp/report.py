from __future__ import annotations

import base64
import html
import json
from pathlib import Path


def _b64(path: Path) -> str:
    if not path or not Path(path).exists():
        return ""
    return base64.b64encode(Path(path).read_bytes()).decode()


def _pill(status: str) -> str:
    cls = "ok" if status == "accepted" else "rev"
    label = "ACCEPTED" if status == "accepted" else "REVIEW"
    return f'<span class="pill {cls}">{label}</span>'


def _src_badge(src: str) -> str:
    return f'<span class="src src-{html.escape(src)}">{html.escape(src)}</span>'


def build_report(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    data = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    m = data["metadata"]

    annotated = _b64(run_dir / "annotated.png")
    rows = []
    for name, f in data["fields"].items():
        conf = f.get("confidence", 0.0)
        crop_rel = None
        crop = run_dir / "crops" / f"{name}.png"
        thumb = _b64(crop) if crop.exists() else ""
        thumb_html = (f'<img class="crop" src="data:image/png;base64,{thumb}"/>'
                      if thumb else '<span class="nocrop">—</span>')
        val = html.escape(str(f.get("value") or "")) or '<span class="empty">(empty)</span>'
        rows.append(f"""
        <tr class="{'r-ok' if f['status']=='accepted' else 'r-rev'}">
          <td>{_pill(f['status'])}</td>
          <td class="fname">{html.escape(name)}</td>
          <td class="val">{val}</td>
          <td><div class="bar"><div class="fill" style="width:{conf*100:.0f}%"></div>
              <span>{conf*100:.0f}%</span></div></td>
          <td>{_src_badge(f.get('source',''))}</td>
          <td>{thumb_html}</td>
        </tr>""")

    review = data.get("review_queue", [])
    review_html = ""
    if review:
        items = "".join(
            f'<li><b>{html.escape(r["field"])}</b> — '
            f'prediction: <code>{html.escape(str(r.get("prediction") or ""))}</code> '
            f'({r.get("confidence",0)*100:.0f}%) · {html.escape(r.get("reason",""))}</li>'
            for r in review)
        review_html = f'<div class="card"><h2>Human review queue ({len(review)})</h2><ul class="rev">{items}</ul></div>'

    cls = data.get("classification", {})
    annotated_html = (f'<img class="page" src="data:image/png;base64,{annotated}"/>'
                      if annotated else "")

    doc = html.escape(data["document"])
    tmpl = html.escape(str(data.get("template_id")))
    note = html.escape(str(m.get("note") or ""))

    htmlpage = f"""<!doctype html><html><head><meta charset="utf-8">
<title>IDP Result — {doc}</title>
<style>
  :root {{ --ok:#1a7f37; --rev:#b54708; --bg:#0f1115; --card:#171a21; --line:#262b36;
          --txt:#e6e9ef; --mut:#9aa4b2; --accent:#4c8dff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--txt); padding:28px; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  h2 {{ font-size:15px; margin:0 0 12px; color:var(--mut); text-transform:uppercase;
        letter-spacing:.05em; }}
  .sub {{ color:var(--mut); margin-bottom:20px; }}
  .wrap {{ display:grid; grid-template-columns:1fr 360px; gap:20px; align-items:start; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:18px; margin-bottom:20px; }}
  .stats {{ display:flex; gap:10px; margin-bottom:18px; }}
  .stat {{ flex:1; background:var(--card); border:1px solid var(--line); border-radius:10px;
           padding:14px; text-align:center; }}
  .stat .n {{ font-size:26px; font-weight:700; }}
  .stat .l {{ color:var(--mut); font-size:12px; text-transform:uppercase; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; color:var(--mut); font-size:11px; text-transform:uppercase;
        padding:8px; border-bottom:1px solid var(--line); }}
  td {{ padding:8px; border-bottom:1px solid var(--line); vertical-align:middle; }}
  .fname {{ font-family:ui-monospace,monospace; color:var(--accent); }}
  .val {{ font-weight:600; }}
  .empty {{ color:var(--mut); font-weight:400; font-style:italic; }}
  .pill {{ font-size:11px; font-weight:700; padding:3px 8px; border-radius:20px; }}
  .pill.ok {{ background:rgba(26,127,55,.18); color:#5fd07f; }}
  .pill.rev {{ background:rgba(181,71,8,.18); color:#f0a35e; }}
  .src {{ font-size:11px; padding:2px 7px; border-radius:6px; background:#222836; color:var(--mut); }}
  .src-vlm {{ background:rgba(76,141,255,.18); color:#8fb6ff; }}
  .src-ocr {{ background:rgba(26,127,55,.18); color:#5fd07f; }}
  .src-human {{ background:rgba(160,120,255,.2); color:#c4adff; }}
  .bar {{ position:relative; width:90px; height:16px; background:#222836; border-radius:8px; }}
  .bar .fill {{ height:100%; background:linear-gradient(90deg,#4c8dff,#5fd07f); border-radius:8px; }}
  .bar span {{ position:absolute; right:6px; top:0; font-size:10px; line-height:16px; }}
  .crop {{ height:30px; max-width:200px; border:1px solid var(--line); border-radius:4px;
           background:#fff; }}
  .nocrop {{ color:var(--mut); }}
  .page {{ width:100%; border:1px solid var(--line); border-radius:10px; }}
  .meta {{ font-size:12px; color:var(--mut); }}
  .meta b {{ color:var(--txt); }}
  ul.rev {{ margin:0; padding-left:18px; }} ul.rev li {{ margin:4px 0; }}
  code {{ background:#222836; padding:1px 6px; border-radius:5px; }}
  .legend {{ font-size:12px; color:var(--mut); margin-top:8px; }}
</style></head><body>
<h1>Intelligent Document Processing — Extraction Result</h1>
<div class="sub">{doc} &nbsp;·&nbsp; template <b>{tmpl}</b> &nbsp;·&nbsp;
  VLM provider <b>{html.escape(str(m.get('vlm_provider')))}</b></div>

<div class="stats">
  <div class="stat"><div class="n">{m['fields_total']}</div><div class="l">Fields</div></div>
  <div class="stat"><div class="n" style="color:var(--ok)">{m['fields_accepted']}</div><div class="l">Auto-accepted</div></div>
  <div class="stat"><div class="n" style="color:var(--rev)">{m['fields_for_review']}</div><div class="l">Human review</div></div>
  <div class="stat"><div class="n">{cls.get('method')}</div><div class="l">Classify · {cls.get('score')}</div></div>
</div>

<div class="wrap">
  <div>
    <div class="card">
      <h2>Extracted fields</h2>
      <table><thead><tr><th>Status</th><th>Field</th><th>Value</th><th>Confidence</th>
      <th>Source</th><th>ROI crop</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
      <div class="legend">source: <span class="src src-vlm">vlm</span> cloud VLM read ·
        <span class="src src-ocr">ocr</span> OCR consensus ·
        <span class="src src-human">human</span> verified ·
        <span class="src">pending_human</span> awaiting review</div>
    </div>
    {review_html}
  </div>
  <div class="card">
    <h2>Located ROIs</h2>
    {annotated_html}
    <div class="legend">green = accepted · red = needs review</div>
    <div class="meta" style="margin-top:14px">
      <div><b>Note:</b> {note}</div>
      <div style="margin-top:6px"><b>Engines:</b> {html.escape(', '.join(m.get('engines',[])))}</div>
      <div><b>Elapsed:</b> {m.get('elapsed_sec')}s</div>
    </div>
  </div>
</div>
</body></html>"""
    out = run_dir / "report.html"
    out.write_text(htmlpage, encoding="utf-8")
    return out
