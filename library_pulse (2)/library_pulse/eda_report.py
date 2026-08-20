"""
Exploratory Data Analysis using Matplotlib + Seaborn.
Run this separately from the Flask app to generate static PNGs for your
project report/appendix -- it demonstrates the Pandas + Matplotlib/Seaborn
half of the DAV toolkit, while the live website uses Plotly for interactivity.

Usage: python3 eda_report.py
Outputs PNGs into eda_output/
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_theme(style="darkgrid", rc={
    "axes.facecolor": "#1C2B4A", "figure.facecolor": "#0F172E",
    "axes.edgecolor": "#B9B2A2", "text.color": "#E7E1D3",
    "axes.labelcolor": "#E7E1D3", "xtick.color": "#E7E1D3", "ytick.color": "#E7E1D3",
    "grid.color": "#2A3B5C",
})
PALETTE = ["#C9A24B", "#3E7C7C", "#A13D3D", "#6E8894", "#8B6F47", "#4C5B72"]

os.makedirs("eda_output", exist_ok=True)

members = pd.read_csv("data/members.csv", parse_dates=["join_date"])
books = pd.read_csv("data/books.csv")
branches = pd.read_csv("data/branches.csv")
tx = pd.read_csv("data/transactions.csv", parse_dates=["checkout_date", "due_date", "return_date"])

tx = tx.merge(books, on="book_id").merge(members, on="member_id", suffixes=("", "_m"))
tx["is_late"] = tx["return_date"].notna() & (tx["return_date"] > tx["due_date"])
tx["month"] = tx["checkout_date"].dt.to_period("M").dt.to_timestamp()

# 1. Checkouts per month (overall demand trend)
plt.figure(figsize=(10, 5))
monthly = tx.groupby("month").size()
plt.plot(monthly.index, monthly.values, color=PALETTE[0], marker="o")
plt.title("Monthly Checkout Volume", fontsize=14)
plt.xlabel("Month"); plt.ylabel("Checkouts")
plt.tight_layout()
plt.savefig("eda_output/01_monthly_checkouts.png", dpi=140)
plt.close()

# 2. Genre distribution
plt.figure(figsize=(9, 5))
order = tx["genre"].value_counts().index
sns.countplot(data=tx, y="genre", order=order, palette=PALETTE * 3)
plt.title("Checkouts by Genre", fontsize=14)
plt.tight_layout()
plt.savefig("eda_output/02_genre_distribution.png", dpi=140)
plt.close()

# 3. Age distribution by membership type
plt.figure(figsize=(9, 5))
sns.boxplot(data=members, x="membership_type", y="age", palette=PALETTE)
plt.title("Age Distribution by Membership Type", fontsize=14)
plt.tight_layout()
plt.savefig("eda_output/03_age_by_membership.png", dpi=140)
plt.close()

# 4. Correlation heatmap of numeric transaction features
plt.figure(figsize=(6, 5))
tx["late_days"] = (tx["return_date"] - tx["due_date"]).dt.days.clip(lower=0).fillna(0)
num = tx[["fine_amount", "late_days", "age"]]
sns.heatmap(num.corr(), annot=True, cmap="mako", vmin=-1, vmax=1)
plt.title("Correlation: Fines, Late Days, Age", fontsize=13)
plt.tight_layout()
plt.savefig("eda_output/04_correlation_heatmap.png", dpi=140)
plt.close()

# 5. Overdue rate by branch
plt.figure(figsize=(8, 5))
overdue_by_branch = tx.groupby("branch_id")["is_late"].mean().sort_values() * 100
sns.barplot(x=overdue_by_branch.values, y=overdue_by_branch.index, palette=PALETTE)
plt.title("Overdue Rate by Branch (%)", fontsize=14)
plt.xlabel("Overdue rate (%)")
plt.tight_layout()
plt.savefig("eda_output/05_overdue_by_branch.png", dpi=140)
plt.close()

print("Saved 5 EDA charts to eda_output/")
