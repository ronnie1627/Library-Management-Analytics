"""
Automates the whole data-setup pipeline so app.py can just call
ensure_data() and have everything ready, with no manual steps.

What it does, only on first run (skips entirely if data already exists):
  1. Tries to fetch real book data from the Open Library API.
     If that fails for any reason (no internet, API down, timeout),
     it's a non-fatal skip -- generate_data.py falls back to realistic
     synthetic books on its own.
  2. Runs generate_data.py to build members/transactions/branches (and
     synthetic books too, if step 1 didn't produce any).

Safe to import and call on every startup -- it's a no-op once the CSVs
already exist, so redeploying or restarting the server doesn't regenerate
(and doesn't re-shuffle) the dataset each time.
"""
import os
import subprocess
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MARKER_FILE = os.path.join(DATA_DIR, "transactions.csv")


def ensure_data():
    if os.path.exists(MARKER_FILE):
        return  # already set up -- nothing to do

    print("First run detected -- setting up the dataset automatically...")
    root = os.path.dirname(os.path.abspath(__file__))

    # Best-effort: try to pull real books from the open-source Open Library
    # API. Non-fatal if it fails -- generate_data.py handles the fallback.
    try:
        subprocess.run(
            [sys.executable, os.path.join(root, "fetch_real_books.py")],
            timeout=60, check=True, cwd=root,
        )
    except Exception as e:
        print(f"Real book fetch skipped ({e.__class__.__name__}: {e}); "
              f"will use synthetic books instead.")

    # Builds members/transactions/branches, and synthetic books too if the
    # fetch above didn't leave a data/books.csv behind.
    subprocess.run(
        [sys.executable, os.path.join(root, "generate_data.py")],
        check=True, cwd=root,
    )
    print("Dataset ready.")
