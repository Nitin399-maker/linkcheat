"""
Tracks which PDFs have already been posted to LinkedIn.
Uses a JSON file (posted_tracker.json) committed back to the repo.
"""

import json
import os
from datetime import datetime, timezone

TRACKER_FILE = "posted_tracker.json"


def load_tracker() -> dict:
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"posted": []}


def save_tracker(tracker: dict) -> None:
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)


def mark_as_posted(pdf_filename: str, post_urn: str) -> None:
    tracker = load_tracker()
    tracker["posted"].append(
        {
            "filename": pdf_filename,
            "post_urn": post_urn,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_tracker(tracker)


def get_posted_filenames() -> list[str]:
    tracker = load_tracker()
    return [entry["filename"] for entry in tracker.get("posted", [])]


def get_next_pdf(pdfs_dir: str = "pdfs") -> str | None:
    """
    Returns the absolute path of the next unposted PDF (alphabetical order),
    or None if all PDFs have been posted.
    """
    if not os.path.isdir(pdfs_dir):
        return None

    all_pdfs = sorted(
        [f for f in os.listdir(pdfs_dir) if f.lower().endswith(".pdf")]
    )
    posted = set(get_posted_filenames())

    for pdf_name in all_pdfs:
        if pdf_name not in posted:
            return os.path.join(pdfs_dir, pdf_name)

    return None  # All PDFs have been posted
