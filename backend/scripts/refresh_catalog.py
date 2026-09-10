"""Refresh the bundled re:Invent 2026 catalog from the official public API.

Run:  python scripts/refresh_catalog.py
Writes: data/reinvent2026_sessions.json (normalized Session objects)

Requires Playwright: pip install playwright && playwright install chromium
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import aws_catalog  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "reinvent2026_sessions.json")


def main():
    print("Scraping the official re:Invent 2026 catalog API…")
    sessions = aws_catalog.fetch_all()
    payload = {"sessions": [s.model_dump(mode="json") for s in sessions]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"Wrote {len(sessions)} sessions to {OUT}")


if __name__ == "__main__":
    main()
