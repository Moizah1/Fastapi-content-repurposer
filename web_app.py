from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from repurposer import (
    ALL_FORMATS,
    DEFAULT_FORMATS,
    TONE_OPTIONS,
    FORMAT_LABELS,
    repurpose,
    repurpose_single_stream,
)

app = FastAPI(title="Content Repurposer")


class RepurposeRequest(BaseModel):
    content: str
    tone: str = "professional"
    formats: list[str] = DEFAULT_FORMATS


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Content Repurposer</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #fafafa; color: #1a1a1a; }}
  h1 {{ font-size: 1.6rem; }}
  textarea {{ width: 100%; min-height: 220px; padding: 10px; font-size: 0.95rem; border-radius: 8px; border: 1px solid #ccc; box-sizing: border-box; }}
  .row {{ display: flex; gap: 20px; margin: 16px 0; flex-wrap: wrap; }}
  fieldset {{ border: 1px solid #ddd; border-radius: 8px; padding: 10px 14px; }}
  button {{ background: #2a2a2a; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 0.95rem; }}
  button:hover {{ background: #444; }}
  .output {{ margin-top: 24px; }}
  .card {{ background: white; border: 1px solid #e2e2e2; border-radius: 10px; padding: 16px; margin-bottom: 16px; white-space: pre-wrap; }}
  .card h3 {{ margin-top: 0; }}
  label {{ font-size: 0.9rem; }}
</style>
</head>
<body>
  <h1>🔁 Content Repurposer</h1>
  <p>Paste a blog post, pick your formats and tone, and generate live.</p>

  <textarea id="content" placeholder="Paste your blog post here..."></textarea>

  <div class="row">
    <fieldset>
      <legend>Formats</legend>
      {format_checkboxes}
    </fieldset>

    <fieldset>
      <legend>Tone</legend>
      {tone_radios}
    </fieldset>
  </div>

  <button onclick="generate()">Generate</button>

  <div class="output" id="output"></div>

<script>
async function generate() {{
  const content = document.getElementById('content').value.trim();
  if (!content) {{ alert('Paste a blog post first.'); return; }}

  const formats = Array.from(document.querySelectorAll('input[name=format]:checked')).map(el => el.value);
  const tone = document.querySelector('input[name=tone]:checked').value;

  const output = document.getElementById('output');
  output.innerHTML = '';

  for (const fmt of formats) {{
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<h3>${{fmt}}</h3><div class="text"></div>`;
    output.appendChild(card);
    const textEl = card.querySelector('.text');

    const resp = await fetch('/stream', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{content, tone, format: fmt}})
    }});
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    while (true) {{
      const {{done, value}} = await reader.read();
      if (done) break;
      textEl.textContent += decoder.decode(value, {{stream: true}});
    }}
  }}
}}
</script>
</body>
</html>
"""


def _build_index_html() -> str:
    format_checkboxes = "\n".join(
        f'<label><input type="checkbox" name="format" value="{fmt}"'
        f'{" checked" if fmt in DEFAULT_FORMATS else ""}> {FORMAT_LABELS.get(fmt, fmt)}</label><br>'
        for fmt in ALL_FORMATS
    )
    tone_radios = "\n".join(
        f'<label><input type="radio" name="tone" value="{tone}"'
        f'{" checked" if tone == "professional" else ""}> {tone}</label><br>'
        for tone in TONE_OPTIONS
    )
    return INDEX_HTML.format(format_checkboxes=format_checkboxes, tone_radios=tone_radios)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _build_index_html()


@app.post("/generate")
async def generate(req: RepurposeRequest):
    """Non-streaming endpoint: returns all requested formats at once (parallel)."""
    results = repurpose(req.content, req.tone, req.formats)
    return results


class StreamRequest(BaseModel):
    content: str
    tone: str = "professional"
    format: str


@app.post("/stream")
async def stream(req: StreamRequest):
    """Streaming endpoint: streams a single format's text as it's generated."""

    def token_generator():
        for chunk in repurpose_single_stream(req.format, req.content, req.tone):
            yield chunk

    return StreamingResponse(token_generator(), media_type="text/plain")
