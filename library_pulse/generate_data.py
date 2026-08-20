"""
Generates synthetic library datasets with deliberately engineered patterns
so the analytics layer has real signal to find:
  - seasonal spikes around exam months (Mar-Apr, Oct-Nov)
  - a genre (Sci-Fi/Tech) trending upward over the last 12 months
  - a subset of members who chronically return late
  - uneven load across branches (Central > North/South > East)
  - weekday/hour borrowing peaks (afternoons, weekdays > weekends)
"""
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import random
import os

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

N_MEMBERS = 800
N_BOOKS = 500
N_TRANSACTIONS = 12000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 12, 31)

BRANCHES = [
    ("BR1", "Central Library", 40.7128, -74.0060, 0.42),
    ("BR2", "North Campus Branch", 40.7580, -73.9855, 0.24),
    ("BR3", "South Community Branch", 40.6782, -73.9442, 0.22),
    ("BR4", "East Reading Room", 40.7306, -73.9352, 0.12),
]
GENRES = ["Fiction", "Sci-Fi", "Technology", "Biography", "History",
          "Mystery", "Romance", "Science", "Self-Help", "Fantasy", "Poetry"]
MEMBER_TYPES = ["Student", "Faculty", "Public"]

# ---------- Branches ----------
branches_df = pd.DataFrame(BRANCHES, columns=["branch_id", "name", "lat", "lng", "weight"])
branches_df.drop(columns="weight").to_csv("data/branches.csv", index=False)

# ---------- Members ----------
member_rows = []
# 12% of members are "chronic late returners" (engineered pattern)
chronic_late_ids = set(random.sample(range(N_MEMBERS), int(N_MEMBERS * 0.12)))
for i in range(N_MEMBERS):
    mtype = np.random.choice(MEMBER_TYPES, p=[0.55, 0.15, 0.30])
    join_date = fake.date_between(start_date=datetime(2020, 1, 1), end_date=START_DATE)
    member_rows.append({
        "member_id": f"M{i+1:04d}",
        "name": fake.name(),
        "age": np.random.randint(18, 25) if mtype == "Student" else np.random.randint(24, 65),
        "membership_type": mtype,
        "branch_id": np.random.choice(branches_df.branch_id, p=branches_df.weight),
        "join_date": join_date,
        "is_chronic_late": i in chronic_late_ids,
    })
members_df = pd.DataFrame(member_rows)
members_df.drop(columns="is_chronic_late").to_csv("data/members.csv", index=False)

# ---------- Books ----------
# If fetch_real_books.py has already been run, data/books.csv holds real
# titles/authors from the Open Library API -- use those instead of making
# up fake ones. Otherwise, fall back to synthetic books as before.
if os.path.exists("data/books.csv") and os.path.getsize("data/books.csv") > 0:
    books_df = pd.read_csv("data/books.csv")
else:
    books_df = pd.DataFrame()

if len(books_df) > 0:
    print(f"Using {len(books_df)} REAL books from data/books.csv (Open Library) -- not regenerating.")
else:
    book_rows = []
    for i in range(N_BOOKS):
        genre = np.random.choice(GENRES)
        book_rows.append({
            "book_id": f"B{i+1:04d}",
            "title": fake.sentence(nb_words=4).rstrip("."),
            "author": fake.name(),
            "genre": genre,
            "publish_year": np.random.randint(1980, 2025),
            "total_copies": np.random.randint(1, 8),
        })
    books_df = pd.DataFrame(book_rows)
    books_df.to_csv("data/books.csv", index=False)

# Derive the working genre list from whatever books actually exist, rather
# than assuming all 11 genres are present -- this keeps things safe if
# fetch_real_books.py only managed to fetch some genres (e.g. one genre
# hit a network error and got skipped).
GENRES = sorted(books_df["genre"].dropna().unique().tolist())

# ---------- Transactions ----------
def seasonal_weight(d):
    # exam-season spikes: March-April & October-November
    if d.month in (3, 4, 10, 11):
        return 1.8
    if d.month in (6, 7, 12):  # summer/winter break dip
        return 0.5
    return 1.0

def weekday_weight(d):
    return 1.3 if d.weekday() < 5 else 0.6

date_range_days = (END_DATE - START_DATE).days
sample_days = np.random.randint(0, date_range_days, size=N_TRANSACTIONS * 2)
candidate_dates = [START_DATE + timedelta(days=int(d)) for d in sample_days]
weights = np.array([seasonal_weight(d) * weekday_weight(d) for d in candidate_dates])
weights = weights / weights.sum()
chosen_idx = np.random.choice(len(candidate_dates), size=N_TRANSACTIONS, replace=False, p=weights)
checkout_dates = [candidate_dates[i] for i in chosen_idx]

# Sci-Fi/Technology trending up over time: bias genre probability by how late the date is
def genre_probs(d):
    progress = (d - START_DATE).days / date_range_days  # 0 -> 1 over the two years
    base = {g: 1.0 for g in GENRES}
    if "Sci-Fi" in base:
        base["Sci-Fi"] = 1.0 + 3.0 * progress
    if "Technology" in base:
        base["Technology"] = 1.0 + 2.2 * progress
    total = sum(base.values())
    return {g: v / total for g, v in base.items()}

member_ids = members_df.member_id.values
member_branch = dict(zip(members_df.member_id, members_df.branch_id))
member_chronic = dict(zip(members_df.member_id, members_df.is_chronic_late))
books_by_genre = books_df.groupby("genre").book_id.apply(list).to_dict()

tx_rows = []
# borrowing volume grows slightly over the two years (engagement growth) + peak afternoon hours
hour_choices = list(range(9, 20))
hour_weights = np.array([1, 1, 2, 3, 4, 5, 5, 4, 4, 3, 2], dtype=float)
hour_weights = hour_weights / hour_weights.sum()

for i, d in enumerate(checkout_dates):
    mid = np.random.choice(member_ids)
    gp = genre_probs(d)
    genre = np.random.choice(list(gp.keys()), p=list(gp.values()))
    bid = random.choice(books_by_genre[genre])
    hour = np.random.choice(hour_choices, p=hour_weights)
    checkout_dt = d.replace(hour=int(hour), minute=np.random.randint(0, 60))
    due_dt = checkout_dt + timedelta(days=14)

    is_chronic = member_chronic.get(mid, False)
    # chronic late returners: 70% chance late; others: 12% chance late
    late_prob = 0.70 if is_chronic else 0.12
    is_late = np.random.rand() < late_prob
    # 6% still checked out (not yet returned) if near end of dataset
    not_returned = (END_DATE - checkout_dt).days < 14 and np.random.rand() < 0.4

    if not_returned:
        return_dt = pd.NaT
        fine = 0.0
    else:
        extra_days = np.random.randint(1, 21) if is_late else np.random.randint(-13, 1)
        return_dt = checkout_dt + timedelta(days=14 + max(extra_days, -13))
        late_days = max((return_dt - due_dt).days, 0)
        fine = round(late_days * 0.25, 2)

    tx_rows.append({
        "transaction_id": f"T{i+1:06d}",
        "member_id": mid,
        "book_id": bid,
        "branch_id": member_branch[mid],
        "checkout_date": checkout_dt,
        "due_date": due_dt,
        "return_date": return_dt,
        "fine_amount": fine,
    })

transactions_df = pd.DataFrame(tx_rows)
transactions_df.to_csv("data/transactions.csv", index=False)

print("Generated:")
print(f"  members.csv       {len(members_df)} rows")
print(f"  books.csv         {len(books_df)} rows")
print(f"  branches.csv      {len(branches_df)} rows")
print(f"  transactions.csv  {len(transactions_df)} rows")
