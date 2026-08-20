"""
Pulls REAL book data (title, author, genre, publish year) from the Open
Library API (openlibrary.org) -- a free, open-source, no-API-key-required
book catalog run by the Internet Archive.

Run this BEFORE generate_data.py:
    python3 fetch_real_books.py
    python3 generate_data.py   <- will detect data/books.csv and use these
                                   real books instead of making up fake ones

Why only books, not members/transactions?
No public API exposes real library circulation data (who borrowed what,
when) -- that's private information every library keeps to itself. Real
book catalog data (titles/authors/subjects), on the other hand, is
genuinely public. So the realistic approach here is: real books, simulated
borrowing activity layered on top -- which is how most library-analytics
projects (student or professional) are actually built.

Docs: https://openlibrary.org/developers/api
"""
import csv
import time
import requests

# Open Library "subjects" endpoint returns real works tagged with a subject.
# Maps Open Library's subject slug -> the genre label used across the site.
SUBJECTS = {
    "fiction": "Fiction",
    "science_fiction": "Sci-Fi",
    "fantasy": "Fantasy",
    "mystery": "Mystery",
    "romance": "Romance",
    "biography": "Biography",
    "history": "History",
    "self-help": "Self-Help",
    "science": "Science",
    "poetry": "Poetry",
    "technology": "Technology",
}

BOOKS_PER_GENRE = 45  # ~500 books total across 11 genres

# Open Library asks that every app identify itself with a descriptive
# User-Agent (their servers are free, shared community infrastructure).
HEADERS = {"User-Agent": "LibraryPulseStudentProject/1.0 (student project; contact: your_email@example.com)"}


def fetch_genre(subject_slug, genre_label, limit):
    url = f"https://openlibrary.org/subjects/{subject_slug}.json?limit={limit}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    rows = []
    for work in data.get("works", []):
        title = (work.get("title") or "Untitled").strip()
        authors = work.get("authors", [])
        author = authors[0]["name"] if authors else "Unknown"
        rows.append({
            "title": title,
            "author": author,
            "genre": genre_label,
            # Open Library's subjects endpoint doesn't always include a
            # publish year; fall back to a reasonable placeholder if absent.
            "publish_year": work.get("first_publish_year") or 2015,
            "total_copies": 3,
        })
    return rows


def main():
    all_books = []
    for slug, label in SUBJECTS.items():
        print(f"Fetching real '{label}' books from Open Library...")
        try:
            all_books.extend(fetch_genre(slug, label, BOOKS_PER_GENRE))
        except requests.RequestException as e:
            print(f"  Skipped {label} due to a network error: {e}")
        time.sleep(1)  # be polite to Open Library's shared infrastructure

    if not all_books:
        print("\nNo real books could be fetched (network/API issue). "
              "Leaving data/books.csv untouched so generate_data.py falls back to synthetic books.")
        return

    with open("data/books.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["book_id", "title", "author", "genre", "publish_year", "total_copies"]
        )
        writer.writeheader()
        for i, book in enumerate(all_books, start=1):
            writer.writerow({"book_id": f"B{i:04d}", **book})

    print(f"\nSaved {len(all_books)} real books to data/books.csv")
    print("Now run: python3 generate_data.py")


if __name__ == "__main__":
    main()
