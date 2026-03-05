"""
LinkedIn PDF Auto-Poster — single-file pipeline.

Pipeline:
  1. Find the next unposted PDF from /pdfs
  2. Extract text from it
  3. Generate a LinkedIn caption via LLM (OpenAI or Gemini)
  4. Post the PDF + caption to LinkedIn
  5. Mark the PDF as posted in tracker

Required environment variables / GitHub Secrets:
  LINKEDIN_ACCESS_TOKEN  — OAuth 2.0 token (w_member_social + r_liteprofile)
  LINKEDIN_PERSON_URN    — e.g. "urn:li:person:XXXXXXXX"
  OPENAI_API_KEY         — OR —
  GEMINI_API_KEY         — at least one LLM key must be set

All LLM calls are made via raw HTTP requests (no openai SDK needed).
"""

import fitz  # PyMuPDF
import json
import os
import sys
import time
import requests
from datetime import datetime, timezone


# ──────────────────────────────────────────────────────────────────
# SECTION 1 — PDF Extraction
# ──────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF, page by page."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"--- Page {page_num + 1} ---\n{text.strip()}")
    doc.close()
    return "\n\n".join(pages_text)


def get_pdf_title(pdf_path: str) -> str:
    """Return a clean title derived from the PDF filename."""
    basename = os.path.basename(pdf_path)
    title = os.path.splitext(basename)[0]
    return title.replace("_", " ").replace("-", " ").title()


# ──────────────────────────────────────────────────────────────────
# SECTION 2 — Caption Generation
# ──────────────────────────────────────────────────────────────────

CAPTION_PROMPT_TEMPLATE = """
You are a LinkedIn content expert who creates viral, engaging posts.

I have a PDF cheatsheet/resource titled: "{title}"

Here is the extracted content from the PDF:
---
{content}
---

Write a compelling LinkedIn post caption that:
1. Starts with a STRONG hook (first line must stop the scroll — make it bold, curious, or provocative)
2. Uses relevant emojis throughout (at least 8-10 emojis)
3. Highlights 3-5 key takeaways from the PDF in a short bullet list
4. Ends with a strong call-to-action encouraging people to SAVE and SHARE the post
5. Includes 5-7 relevant hashtags at the end
6. Is between 150-250 words total
7. Creates FOMO — the reader must feel they NEED to open this PDF

Return ONLY the caption text, nothing else.
"""


def generate_caption(title: str, content: str) -> str:
    """Generate a LinkedIn caption via raw HTTP — OpenAI (priority) or Gemini."""
    prompt = CAPTION_PROMPT_TEMPLATE.format(title=title, content=content[:4000])

    if os.environ.get("OPENAI_API_KEY"):
        print("Using OpenAI GPT-4o for caption generation...")
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}]
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    elif os.environ.get("GEMINI_API_KEY"):
        print("Using Google Gemini for caption generation...")
        api_key = os.environ["GEMINI_API_KEY"]
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        raise EnvironmentError(
            "No LLM API key found. Set either OPENAI_API_KEY or GEMINI_API_KEY "
            "as environment variables / GitHub Secrets."
        )


# ──────────────────────────────────────────────────────────────────
# SECTION 3 — LinkedIn Posting
# ──────────────────────────────────────────────────────────────────

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def _li_headers(extra: dict = None) -> dict:
    base = {
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if extra:
        base.update(extra)
    return base


def _get_person_urn() -> str:
    urn = os.environ.get("LINKEDIN_PERSON_URN", "").strip()
    if not urn:
        raise EnvironmentError(
            "LINKEDIN_PERSON_URN is not set. "
            "Find it at https://api.linkedin.com/v2/me and add it as a secret."
        )
    return urn


def post_pdf_to_linkedin(pdf_path: str, caption: str, pdf_title: str) -> str:
    """Upload PDF and create LinkedIn post. Returns the post URN."""
    person_urn = _get_person_urn()

    # Step 1 — Register upload
    print("  [1/3] Registering upload...")
    reg_url = f"{LINKEDIN_API_BASE}/assets?action=registerUpload"
    reg_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-document"],
            "owner": person_urn,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    resp = requests.post(reg_url, json=reg_payload, headers=_li_headers({"Content-Type": "application/json"}))
    resp.raise_for_status()
    data = resp.json()
    upload_url = data["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = data["value"]["asset"]

    # Step 2 — Upload PDF bytes
    print("  [2/3] Uploading PDF bytes...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    resp = requests.put(
        upload_url,
        data=pdf_bytes,
        headers={
            "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
            "Content-Type": "application/octet-stream",
        },
    )
    resp.raise_for_status()
    time.sleep(3)  # Let LinkedIn process the upload

    # Step 3 — Create post
    print("  [3/3] Creating LinkedIn post...")
    post_payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "DOCUMENT",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": pdf_title},
                        "media": asset_urn,
                        "title": {"text": pdf_title},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = requests.post(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        json=post_payload,
        headers=_li_headers({"Content-Type": "application/json"}),
    )
    resp.raise_for_status()
    post_urn = resp.headers.get("x-restli-id", "unknown")
    print(f"  Post created! URN: {post_urn}")
    return post_urn


# ──────────────────────────────────────────────────────────────────
# SECTION 4 — Pipeline Orchestrator
# ──────────────────────────────────────────────────────────────────

def run_pipeline():
    print("=" * 60)
    print("LinkedIn PDF Post Pipeline")
    print("=" * 60)

    # ── Step 1: Find next PDF ──────────────────────────────────────
    print("\n[Step 1] Looking for next unposted PDF...")
    from tracker import get_next_pdf, mark_as_posted
    pdf_path = get_next_pdf("pdfs")

    if pdf_path is None:
        print("No unposted PDFs found in /pdfs directory.")
        print("Add more PDFs to the /pdfs folder to continue posting.")
        sys.exit(0)

    pdf_filename = os.path.basename(pdf_path)
    pdf_title = get_pdf_title(pdf_path)
    print(f"  Found: {pdf_filename} → Title: \"{pdf_title}\"")

    # ── Step 2: Extract text ───────────────────────────────────────
    print("\n[Step 2] Extracting text from PDF...")
    content = extract_text_from_pdf(pdf_path)
    word_count = len(content.split())
    print(f"  Extracted {word_count} words from {pdf_filename}")
    if word_count < 20:
        print("  Warning: Very little text extracted. PDF might be image-based.")

    # ── Step 3: Generate caption ───────────────────────────────────
    print("\n[Step 3] Generating LinkedIn caption via LLM...")
    caption = generate_caption(pdf_title, content)
    print("\n  --- Generated Caption ---")
    print(caption)
    print("  -------------------------\n")

    # ── Step 4: Post to LinkedIn ───────────────────────────────────
    print("[Step 4] Posting to LinkedIn...")
    post_urn = post_pdf_to_linkedin(pdf_path, caption, pdf_title)

    # ── Step 5: Mark as posted ─────────────────────────────────────
    print("\n[Step 5] Updating tracker...")
    mark_as_posted(pdf_filename, post_urn)
    print(f"  Marked '{pdf_filename}' as posted.")

    print("\n" + "=" * 60)
    print(f"SUCCESS: Posted '{pdf_title}' to LinkedIn!")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
