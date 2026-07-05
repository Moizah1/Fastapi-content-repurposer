import anthropic
import concurrent.futures
import os
import sys

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

TONE_OPTIONS = ["professional", "casual", "witty", "inspirational"]

PROMPTS = {
    "twitter": """You are a social media expert. Convert the following blog post into an engaging Twitter/X thread with {tone} tone.
Format it as numbered tweets (1/, 2/, 3/...). Each tweet must be under 280 characters.
Use hooks, line breaks within tweets for readability, and end with a strong CTA.
Output ONLY the thread, no intro text.

BLOG POST:
{content}""",

    "linkedin": """You are a LinkedIn content strategist. Convert the following blog post into a {tone} LinkedIn post.
Structure: strong opening hook (1-2 lines), 3-5 key insights with line breaks, a relatable story or example, CTA at the end.
Use short paragraphs. No hashtag overload (max 3). Around 200-300 words.
Output ONLY the LinkedIn post, no intro text.

BLOG POST:
{content}""",

    "email": """You are an email newsletter writer. Convert the following blog post into a {tone} email newsletter section.
Include: a catchy subject line (prefixed with "Subject: "), a warm opening sentence, the key value in 2-3 short paragraphs, and a CTA button text.
Keep it concise and scannable. Around 150-200 words.
Output ONLY the email content, no intro text.

BLOG POST:
{content}""",

    "instagram": """You are an Instagram content creator. Convert the following blog post into a {tone} Instagram caption.
Structure: a scroll-stopping first line (shows before "more"), 2-4 short paragraphs with line breaks and relevant emojis,
a clear CTA (e.g. "Save this for later", "Tag a friend"), and a block of 5-10 relevant hashtags at the very end.
Keep the caption itself under 200 words, not counting hashtags.
Output ONLY the caption, no intro text.

BLOG POST:
{content}""",

    "youtube": """You are a YouTube content strategist. Convert the following blog post into a {tone} YouTube video description.
Include: a 2-3 sentence hook/summary optimized for search, a short list of key points covered (as bullet lines),
a placeholder timestamps section (e.g. "00:00 Intro", "00:00 Topic 1", ...), a CTA to like/subscribe,
and a line of 3-5 relevant hashtags at the end.
Output ONLY the description, no intro text.

BLOG POST:
{content}""",

    "reddit": """You are an experienced Reddit poster who understands community norms and dislikes anything that sounds like an ad.
Convert the following blog post into a {tone} Reddit post.
Structure: a plain, honest title line (prefixed with "Title: "), followed by a body written in first person,
conversational, non-salesy language. Share the core insight like you're telling a community something useful,
acknowledge nuance or counterpoints where relevant, and end by inviting discussion (a genuine question), not a CTA.
Output ONLY the title line and body, no other intro text.

BLOG POST:
{content}""",
}

FORMAT_LABELS = {
    "twitter": "🐦  TWITTER / X THREAD",
    "linkedin": "💼  LINKEDIN POST",
    "email": "📧  EMAIL NEWSLETTER",
    "instagram": "📸  INSTAGRAM CAPTION",
    "youtube": "▶️  YOUTUBE DESCRIPTION",
    "reddit": "👽  REDDIT POST",
}

ALL_FORMATS = list(PROMPTS.keys())
DEFAULT_FORMATS = ["twitter", "linkedin", "email"]

MODEL = "claude-sonnet-4-6"


# ─── Core generation ────────────────────────────────────────────────────────

def repurpose_single(format_name: str, content: str, tone: str) -> tuple[str, str]:
    """Call the API for a single output format (non-streaming). Returns (format_name, result_text)."""
    prompt = PROMPTS[format_name].format(tone=tone, content=content)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return format_name, message.content[0].text


def repurpose(content: str, tone: str = "professional", formats: list[str] | None = None) -> dict[str, str]:
    """
    Repurpose a blog post into multiple formats in parallel (non-streaming).

    Args:
        content: The blog post text.
        tone:    One of 'professional', 'casual', 'witty', 'inspirational'.
        formats: Which formats to generate. Defaults to twitter/linkedin/email.

    Returns:
        Dict mapping format name -> generated text.
    """
    if tone not in TONE_OPTIONS:
        raise ValueError(f"Tone must be one of: {TONE_OPTIONS}")

    formats = formats or DEFAULT_FORMATS
    invalid = [f for f in formats if f not in PROMPTS]
    if invalid:
        raise ValueError(f"Unknown format(s): {invalid}. Valid options: {ALL_FORMATS}")

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(formats)) as executor:
        futures = {
            executor.submit(repurpose_single, fmt, content, tone): fmt
            for fmt in formats
        }
        for future in concurrent.futures.as_completed(futures):
            fmt_name, text = future.result()
            results[fmt_name] = text

    return results


def repurpose_single_stream(format_name: str, content: str, tone: str):
    """
    Stream a single format's output chunk by chunk (generator of text deltas).
    Streams formats one at a time (not in parallel) so output can be displayed live.
    """
    prompt = PROMPTS[format_name].format(tone=tone, content=content)
    with client.messages.stream(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def repurpose_stream_all(content: str, tone: str = "professional", formats: list[str] | None = None) -> dict[str, str]:
    """
    Stream each requested format's output live to stdout, one format after another.
    Returns the same dict shape as repurpose() once everything has finished streaming.
    """
    if tone not in TONE_OPTIONS:
        raise ValueError(f"Tone must be one of: {TONE_OPTIONS}")

    formats = formats or DEFAULT_FORMATS
    results = {}
    divider = "\n" + "─" * 60 + "\n"

    for fmt in formats:
        print(divider)
        print(FORMAT_LABELS.get(fmt, fmt.upper()))
        print(divider)
        chunks = []
        for text in repurpose_single_stream(fmt, content, tone):
            print(text, end="", flush=True)
            chunks.append(text)
        print()  # newline after this format finishes
        results[fmt] = "".join(chunks)

    print("\n" + "─" * 60)
    return results


# ─── Display / persistence ──────────────────────────────────────────────────

def print_results(results: dict[str, str]) -> None:
    """Pretty-print the repurposed outputs (used for non-streaming mode)."""
    divider = "\n" + "─" * 60 + "\n"
    for fmt, text in results.items():
        print(divider)
        print(FORMAT_LABELS.get(fmt, fmt.upper()))
        print(divider)
        print(text)
    print("\n" + "─" * 60)


def save_results(results: dict[str, str], base_filename: str = "output") -> None:
    """Save each format to a separate .txt file."""
    for fmt, text in results.items():
        filename = f"{base_filename}_{fmt}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  Saved: {filename}")


def save_to_notion(results: dict[str, str], page_title: str = "Repurposed Content") -> None:
    """
    Save each format as a page in a Notion database.

    Requires environment variables:
        NOTION_API_KEY      - an internal integration token (share the target
                               database with this integration in Notion first)
        NOTION_DATABASE_ID  - the database to create pages in

    Each generated format is created as its own page, with the content placed
    into paragraph blocks (split on blank lines to keep each block under
    Notion's ~2000 character limit).
    """
    import requests

    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        print("  Skipped Notion export: set NOTION_API_KEY and NOTION_DATABASE_ID env vars.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    for fmt, text in results.items():
        paragraphs = [p for p in text.split("\n\n") if p.strip()] or [text]
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": p[:2000]}}]
                },
            }
            for p in paragraphs
        ]

        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": f"{page_title} — {fmt}"}}]}
            },
            "children": children,
        }

        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        if resp.status_code == 200:
            print(f"  Saved to Notion: {fmt}")
        else:
            print(f"  Failed to save '{fmt}' to Notion ({resp.status_code}): {resp.text[:200]}")


def save_to_google_docs(results: dict[str, str], doc_title: str = "Repurposed Content") -> None:
    """
    Save all formats into a single Google Doc, one section per format.

    Requires:
        - The `google-api-python-client`, `google-auth-httplib2`, and
          `google-auth-oauthlib` packages installed.
        - A Google Cloud OAuth client secret file. Set its path via the
          GOOGLE_CLIENT_SECRET_FILE env var (defaults to "client_secret.json").
        - On first run, a browser window opens for you to grant access; a
          token is cached to "token.json" for subsequent runs.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("  Skipped Google Docs export: run "
              "`pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`")
        return

    SCOPES = ["https://www.googleapis.com/auth/documents"]
    client_secret_file = os.environ.get("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")

    if not os.path.exists(client_secret_file):
        print(f"  Skipped Google Docs export: client secret file not found at '{client_secret_file}'. "
              f"Set GOOGLE_CLIENT_SECRET_FILE or create one in Google Cloud Console.")
        return

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    service = build("docs", "v1", credentials=creds)
    doc = service.documents().create(body={"title": doc_title}).execute()
    document_id = doc["documentId"]

    # Build the full text body first, then insert it in one batch request.
    body_text = ""
    for fmt, text in results.items():
        body_text += f"{FORMAT_LABELS.get(fmt, fmt.upper())}\n\n{text}\n\n{'-' * 40}\n\n"

    requests_batch = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": body_text,
            }
        }
    ]
    service.documents().batchUpdate(documentId=document_id, body={"requests": requests_batch}).execute()

    print(f"  Saved to Google Docs: https://docs.google.com/document/d/{document_id}/edit")


# ─── CLI entry point ────────────────────────────────────────────────────────

def _prompt_formats() -> list[str]:
    print("\nChoose formats to generate (comma-separated numbers, or Enter for default: twitter, linkedin, email):")
    for i, fmt in enumerate(ALL_FORMATS, 1):
        print(f"  {i}. {fmt}")
    choice = input("Enter numbers (e.g. 1,3,5): ").strip()
    if not choice:
        return DEFAULT_FORMATS
    picked = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(ALL_FORMATS):
            picked.append(ALL_FORMATS[int(part) - 1])
    return picked or DEFAULT_FORMATS


def main():
    print("\n🔁  Content Repurposer")
    print("─" * 40)

    # Get input
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Loaded: {filepath} ({len(content)} chars)")
    else:
        print("Paste your blog post below. Press Enter twice then Ctrl+D (Mac/Linux) or Ctrl+Z (Windows) when done:\n")
        lines = []
        try:
            for line in sys.stdin:
                lines.append(line)
        except EOFError:
            pass
        content = "".join(lines).strip()

    if not content:
        print("No content provided. Exiting.")
        sys.exit(1)

    # Choose formats
    formats = _prompt_formats()

    # Choose tone
    print("\nChoose tone:")
    for i, t in enumerate(TONE_OPTIONS, 1):
        print(f"  {i}. {t}")
    choice = input("Enter number (default 1 = professional): ").strip()
    tone = TONE_OPTIONS[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= 4 else "professional"

    # Choose streaming vs parallel
    stream_choice = input("\nStream output live instead of generating in parallel? (y/n, default n): ").strip().lower()

    if stream_choice == "y":
        print(f"\n⏳  Streaming with '{tone}' tone (one format at a time)...")
        results = repurpose_stream_all(content, tone, formats)
    else:
        print(f"\n⏳  Repurposing with '{tone}' tone (calling API in parallel)...")
        results = repurpose(content, tone, formats)
        print_results(results)

    # Optionally save
    save = input("\nSave results? (file / notion / gdocs / n): ").strip().lower()
    if save == "file":
        save_results(results)
    elif save == "notion":
        save_to_notion(results)
    elif save == "gdocs":
        save_to_google_docs(results)

    print("\n✅  Done!\n")


if __name__ == "__main__":
    main()
