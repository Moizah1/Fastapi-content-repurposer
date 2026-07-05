# 🔁 Content Repurposer

Turn a single blog post into multiple ready-to-post formats — Twitter/X thread, LinkedIn post, email newsletter, Instagram caption, YouTube description, and Reddit post — using Claude. Available as a CLI tool or a simple web app, with optional export to Notion or Google Docs.

## Features

- **Six output formats** — Twitter/X thread, LinkedIn post, email newsletter, Instagram caption, YouTube description, and Reddit post. Pick any combination.
- **Tone control** — choose from `professional`, `casual`, `witty`, or `inspirational`.
- **Format-aware prompts** — each output follows platform-specific best practices (character limits, hooks, CTAs, hashtag limits, community norms, etc.).
- **Parallel or streaming generation** — generate all formats at once in parallel, or stream text live as it's written.
- **CLI or web UI** — use it from the terminal, or run a lightweight FastAPI + HTML front-end in your browser.
- **Export options** — save to local `.txt` files, push pages to a Notion database, or write everything into a single Google Doc.

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

## Installation

```bash
pip install -r requirements.txt
```

`requirements.txt` is split into a core dependency (`anthropic`) and optional ones for the web UI (`fastapi`, `uvicorn`), Notion export (`requests`), and Google Docs export (`google-api-python-client` and friends). Install only what you need if you'd rather keep things lean.

Set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here" #for MAC
set ANTHROPIC_API_KEY="your-api-key-here"  #for Windows
```

## Usage

### CLI — interactive mode

```bash
python repurposer.py
```

Paste your content, then press `Enter` twice followed by `Ctrl+D` (Mac/Linux) or `Ctrl+Z` (Windows) to submit. You'll then be asked to:

1. Pick which formats to generate (comma-separated numbers).
2. Pick a tone.
3. Choose whether to stream output live or generate everything in parallel.
4. Optionally save results — to files, Notion, or Google Docs.

### CLI — file input mode

```bash
python repurposer.py my_blog_post.txt
```

### Web UI

```bash
uvicorn web_app:app --reload
```

Then open `http://127.0.0.1:8000`. Paste your post, check the formats you want, pick a tone, and hit **Generate** — each format streams into its own card in real time.

## Using it as a library

```python
from repurposer import repurpose, repurpose_stream_all, print_results

content = "Your blog post text here..."

# Parallel, non-streaming
results = repurpose(content, tone="witty", formats=["twitter", "instagram", "reddit"])
print_results(results)

# Streamed live to stdout, one format at a time
results = repurpose_stream_all(content, tone="witty", formats=["linkedin"])
```

## Exporting results

```python
from repurposer import save_results, save_to_notion, save_to_google_docs

save_results(results)                 # writes output_<format>.txt for each format
save_to_notion(results)               # requires NOTION_API_KEY + NOTION_DATABASE_ID env vars
save_to_google_docs(results)          # requires a Google Cloud OAuth client secret file
```

**Notion setup:**
1. Create an internal integration at [notion.so/my-integrations](https://www.notion.so/my-integrations) and copy its token.
2. Share your target database with that integration.
3. Set `NOTION_API_KEY` and `NOTION_DATABASE_ID` as environment variables.

**Google Docs setup:**
1. Create OAuth 2.0 credentials (Desktop app type) in the Google Cloud Console with the Docs API enabled.
2. Download the client secret JSON and point to it via `GOOGLE_CLIENT_SECRET_FILE` (defaults to `client_secret.json` in the working directory).
3. On first run, a browser window opens to authorize access; a `token.json` is cached for future runs.

## How it works

Each format has a tailored prompt describing that platform's structure and constraints. In parallel mode, all requested formats are sent to Claude (`claude-sonnet-4-6`) concurrently via a thread pool. In streaming mode, formats are generated one at a time using `client.messages.stream()` so text appears as it's written.

## Project structure

```
repurposer.py       # Core generation logic, export functions, and CLI
web_app.py           # FastAPI web UI (optional)
requirements.txt     # Dependencies (core + optional feature groups)
```

## License

MIT
