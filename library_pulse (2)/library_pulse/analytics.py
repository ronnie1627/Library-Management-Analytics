"""
All data loading, Pandas transformations, and Plotly figure construction
for the Library Pulse dashboard. Flask routes call these functions and
send fig.to_json() straight to the browser for Plotly.js to render.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from datetime import datetime

PALETTE = ["#7C93B3", "#5B7A99", "#4A6483", "#94A8C2", "#3E5670", "#6B85A3"]
TEMPLATE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Sans, sans-serif", color="#D8DEE9", size=13),
    margin=dict(l=40, r=20, t=16, b=40),
    colorway=PALETTE,
)

def style(fig, title=None):
    fig.update_layout(**TEMPLATE_LAYOUT)
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=16, family="Fraunces, serif")))
    fig.update_xaxes(gridcolor="rgba(231,225,211,0.08)", zerolinecolor="rgba(231,225,211,0.15)")
    fig.update_yaxes(gridcolor="rgba(231,225,211,0.08)", zerolinecolor="rgba(231,225,211,0.15)")
    return fig


class LibraryData:
    def __init__(self, data_dir="data"):
        self.members = pd.read_csv(f"{data_dir}/members.csv", parse_dates=["join_date"])
        self.books = pd.read_csv(f"{data_dir}/books.csv")
        self.branches = pd.read_csv(f"{data_dir}/branches.csv")
        self.tx = pd.read_csv(
            f"{data_dir}/transactions.csv",
            parse_dates=["checkout_date", "due_date", "return_date"],
        )
        self._enrich()

    def _enrich(self):
        tx = self.tx.merge(self.books, on="book_id", how="left") \
                     .merge(self.members, on="member_id", how="left", suffixes=("", "_member")) \
                     .merge(self.branches, on="branch_id", how="left", suffixes=("", "_branch"))
        tx["is_returned"] = tx["return_date"].notna()
        tx["is_late"] = tx["is_returned"] & (tx["return_date"] > tx["due_date"])
        tx["late_days"] = np.where(tx["is_late"], (tx["return_date"] - tx["due_date"]).dt.days, 0)
        tx["month"] = tx["checkout_date"].dt.to_period("M").dt.to_timestamp()
        tx["weekday"] = tx["checkout_date"].dt.day_name()
        tx["hour"] = tx["checkout_date"].dt.hour
        self.tx = tx

    # ---------------- KPIs ----------------
    def kpis(self):
        tx = self.tx
        total_checkouts = len(tx)
        active_members = tx["member_id"].nunique()
        overdue_rate = tx["is_late"].mean() * 100
        total_fines = tx["fine_amount"].sum()
        return {
            "total_checkouts": f"{total_checkouts:,}",
            "active_members": f"{active_members:,}",
            "overdue_rate": f"{overdue_rate:.1f}%",
            "total_fines": f"${total_fines:,.2f}",
            "raw": {
                "total_checkouts": total_checkouts,
                "active_members": active_members,
                "overdue_rate": round(overdue_rate, 1),
                "total_fines": round(total_fines, 2),
            },
        }

    # ---------------- Genre trend ----------------
    def genre_trend_fig(self):
        monthly = self.tx.groupby(["month", "genre"]).size().reset_index(name="checkouts")
        top_genres = self.tx["genre"].value_counts().head(6).index.tolist()
        monthly = monthly[monthly["genre"].isin(top_genres)]
        fig = px.area(monthly, x="month", y="checkouts", color="genre",
                       groupnorm=None, color_discrete_sequence=PALETTE)
        return style(fig)

    # ---------------- Heatmap: weekday x hour ----------------
    def borrow_heatmap_fig(self):
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot = self.tx.groupby(["weekday", "hour"]).size().reset_index(name="count")
        pivot = pivot.pivot(index="weekday", columns="hour", values="count").reindex(order).fillna(0)
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index,
            colorscale=[[0, "#1B2430"], [0.5, "#4A6483"], [1, "#94A8C2"]],
            hovertemplate="%{y}, %{x}:00 &mdash; %{z} checkouts<extra></extra>",
        ))
        fig.update_yaxes(autorange="reversed")
        return style(fig)

    # ---------------- Branch comparison ----------------
    def branch_fig(self):
        g = self.tx.groupby("name_branch").agg(
            checkouts=("transaction_id", "count"),
            avg_late_days=("late_days", "mean"),
        ).reset_index().sort_values("checkouts", ascending=True)
        fig = go.Figure(go.Bar(
            x=g["checkouts"], y=g["name_branch"], orientation="h",
            marker_color=PALETTE[1],
            hovertemplate="%{y}: %{x} checkouts<extra></extra>",
        ))
        return style(fig)

    # ---------------- Member segmentation (RFM + KMeans) ----------------
    def segmentation(self):
        tx = self.tx
        snapshot = tx["checkout_date"].max() + pd.Timedelta(days=1)
        rfm = tx.groupby("member_id").agg(
            recency=("checkout_date", lambda s: (snapshot - s.max()).days),
            frequency=("transaction_id", "count"),
            monetary=("fine_amount", "sum"),
        ).reset_index()

        X = StandardScaler().fit_transform(rfm[["recency", "frequency", "monetary"]])
        km = KMeans(n_clusters=4, random_state=42, n_init=10)
        rfm["cluster"] = km.fit_predict(X)

        # label clusters by their characteristics rather than arbitrary numbers
        summary = rfm.groupby("cluster")[["recency", "frequency", "monetary"]].mean()
        labels = {}
        for c in summary.index:
            row = summary.loc[c]
            if row["frequency"] >= summary["frequency"].median() and row["recency"] <= summary["recency"].median():
                labels[c] = "Power Readers"
            elif row["recency"] > summary["recency"].median() * 1.3:
                labels[c] = "Lapsing"
            elif row["monetary"] > summary["monetary"].median() * 1.2:
                labels[c] = "Fine-Prone"
            else:
                labels[c] = "Occasional"
        rfm["segment"] = rfm["cluster"].map(labels)

        fig = px.scatter(
            rfm, x="recency", y="frequency", size="monetary", color="segment",
            hover_data=["member_id"], size_max=28, color_discrete_sequence=PALETTE,
        )
        fig.update_layout(legend_title_text="Segment")
        return style(fig), rfm

    def segment_counts_fig(self, rfm):
        counts = rfm["segment"].value_counts().reset_index()
        counts.columns = ["segment", "members"]
        fig = go.Figure(go.Bar(x=counts["segment"], y=counts["members"], marker_color=PALETTE))
        return style(fig)

    # ---------------- Overdue by membership type ----------------
    def overdue_fig(self):
        g = self.tx.groupby("membership_type")["is_late"].mean().reset_index()
        g["is_late"] *= 100
        fig = go.Figure(go.Bar(x=g["membership_type"], y=g["is_late"], marker_color=PALETTE[2]))
        fig.update_yaxes(title="Overdue rate (%)")
        return style(fig)

    # ---------------- Top books ----------------
    def top_books(self, n=10, genre=None):
        tx = self.tx if not genre or genre == "All" else self.tx[self.tx["genre"] == genre]
        top = tx.groupby(["book_id", "title", "author", "genre"]).size() \
                .reset_index(name="checkouts").sort_values("checkouts", ascending=False).head(n)
        return top

    def top_books_fig(self, genre=None):
        top = self.top_books(10, genre).sort_values("checkouts")
        fig = go.Figure(go.Bar(x=top["checkouts"], y=top["title"], orientation="h",
                                marker_color=PALETTE[0]))
        return style(fig)

    # ---------------- Recommendations (co-occurrence) ----------------
    def recommend(self, book_id, n=5):
        tx = self.tx
        members_who_read = tx[tx["book_id"] == book_id]["member_id"].unique()
        co = tx[tx["member_id"].isin(members_who_read) & (tx["book_id"] != book_id)]
        counts = co.groupby(["book_id", "title", "author"]).size() \
                   .reset_index(name="shared_readers") \
                   .sort_values("shared_readers", ascending=False).head(n)
        return counts

    def genres(self):
        return ["All"] + sorted(self.tx["genre"].dropna().unique().tolist())

    # ---------------- Excel export ----------------
    def export_excel(self):
        """Builds a multi-sheet Excel workbook summarizing the whole report."""
        import io
        buffer = io.BytesIO()

        kpis = self.kpis()
        kpi_df = pd.DataFrame([
            {"Metric": "Total Checkouts", "Value": kpis["total_checkouts"]},
            {"Metric": "Active Members", "Value": kpis["active_members"]},
            {"Metric": "Overdue Rate", "Value": kpis["overdue_rate"]},
            {"Metric": "Fines Collected", "Value": kpis["total_fines"]},
        ])

        _, rfm = self.segmentation()
        segment_summary = rfm.groupby("segment").agg(
            members=("member_id", "count"),
            avg_recency_days=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_fines=("monetary", "mean"),
        ).round(1).reset_index()

        branch_summary = self.tx.groupby("name_branch").agg(
            checkouts=("transaction_id", "count"),
            avg_late_days=("late_days", "mean"),
            total_fines=("fine_amount", "sum"),
        ).round(2).reset_index()

        overdue_by_type = self.tx.groupby("membership_type")["is_late"].mean().reset_index()
        overdue_by_type["is_late"] = (overdue_by_type["is_late"] * 100).round(1)
        overdue_by_type.columns = ["Membership Type", "Overdue Rate (%)"]

        top_books = self.top_books(20)
        genre_monthly = self.tx.groupby(["month", "genre"]).size().reset_index(name="checkouts")
        genre_monthly["month"] = genre_monthly["month"].dt.strftime("%Y-%m")

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            kpi_df.to_excel(writer, sheet_name="Overview", index=False)
            segment_summary.to_excel(writer, sheet_name="Member Segments", index=False)
            branch_summary.to_excel(writer, sheet_name="Branches", index=False)
            overdue_by_type.to_excel(writer, sheet_name="Overdue by Type", index=False)
            top_books.to_excel(writer, sheet_name="Top 20 Books", index=False)
            genre_monthly.to_excel(writer, sheet_name="Genre Trend (Monthly)", index=False)

        buffer.seek(0)
        return buffer
