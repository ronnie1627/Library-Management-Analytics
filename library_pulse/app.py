from flask import Flask, render_template, request, jsonify
import plotly
import json
import os
from bootstrap import ensure_data

ensure_data()  # auto-sets-up the dataset on first run, no manual steps needed

from analytics import LibraryData

app = Flask(__name__)
lib = LibraryData("data")


def fig_json(fig):
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@app.route("/")
def index():
    kpis = lib.kpis()
    genre_fig = fig_json(lib.genre_trend_fig())
    heatmap_fig = fig_json(lib.borrow_heatmap_fig())
    branch_fig = fig_json(lib.branch_fig())
    return render_template("index.html", kpis=kpis, genre_fig=genre_fig,
                            heatmap_fig=heatmap_fig, branch_fig=branch_fig)


@app.route("/members")
def members_page():
    seg_fig, rfm = lib.segmentation()
    counts_fig = lib.segment_counts_fig(rfm)
    overdue_fig = lib.overdue_fig()
    segment_summary = rfm.groupby("segment").agg(
        members=("member_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_fines=("monetary", "mean"),
    ).round(1).reset_index().to_dict(orient="records")
    return render_template("members.html",
                            seg_fig=fig_json(seg_fig),
                            counts_fig=fig_json(counts_fig),
                            overdue_fig=fig_json(overdue_fig),
                            segment_summary=segment_summary)


@app.route("/trends")
def trends_page():
    genre = request.args.get("genre", "All")
    genres = lib.genres()
    top_fig = fig_json(lib.top_books_fig(genre))
    genre_fig = fig_json(lib.genre_trend_fig())
    top_books = lib.top_books(10, genre).to_dict(orient="records")
    return render_template("trends.html", genres=genres, selected_genre=genre,
                            top_fig=top_fig, genre_fig=genre_fig, top_books=top_books)


@app.route("/branches")
def branches_page():
    branch_fig = fig_json(lib.branch_fig())
    heatmap_fig = fig_json(lib.borrow_heatmap_fig())
    branch_table = lib.tx.groupby("name_branch").agg(
        checkouts=("transaction_id", "count"),
        avg_late_days=("late_days", "mean"),
        total_fines=("fine_amount", "sum"),
    ).round(2).reset_index().to_dict(orient="records")
    return render_template("branches.html", branch_fig=branch_fig,
                            heatmap_fig=heatmap_fig, branch_table=branch_table)


@app.route("/book/<book_id>")
def book_detail(book_id):
    book = lib.books[lib.books["book_id"] == book_id].iloc[0].to_dict()
    recs = lib.recommend(book_id).to_dict(orient="records")
    checkouts = int((lib.tx["book_id"] == book_id).sum())
    return render_template("book_detail.html", book=book, recs=recs, checkouts=checkouts)


@app.route("/insights")
def insights_page():
    kpis = lib.kpis()
    return render_template("insights.html", kpis=kpis)


@app.route("/api/books")
def api_books():
    q = request.args.get("q", "").lower()
    matches = lib.books[lib.books["title"].str.lower().str.contains(q)].head(15)
    return jsonify(matches.to_dict(orient="records"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
