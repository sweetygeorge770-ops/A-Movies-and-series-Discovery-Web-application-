from flask import Flask, render_template, redirect, url_for, request
import requests
import sqlite3
from dotenv import dotenv_values

config = dotenv_values(".env")

app = Flask(__name__)

TMDB_TOKEN = config.get("TMDB_TOKEN")
# ==============================
# DATABASE
# ==============================

def get_db():
    conn = sqlite3.connect("cineverse.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER UNIQUE,
            title TEXT,
            poster_path TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS completed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER UNIQUE,
            title TEXT,
            poster_path TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()
def get_tmdb_data(url):
    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )

    response.raise_for_status()

    return response.json()


# ==============================
# HOME PAGE
# ==============================


# ==============================
# OLD MOVIE LINK
# ==============================
# Your current Wednesday card uses /movie
# So this redirects it to Wednesday's TMDB page.

@app.route("/movie")
def movie_default():
    return redirect(url_for("movie", movie_id=119051))
@app.route("/")
def home():

    india_movies = get_tmdb_data(
    "https://api.themoviedb.org/3/discover/movie?with_origin_country=IN&sort_by=popularity.desc"
)

    global_movies = get_tmdb_data(
        "https://api.themoviedb.org/3/trending/movie/day"
    )

    return render_template(
        "index.html",
        india_movies=india_movies.get("results", []),
        global_movies=global_movies.get("results", [])
    )

# ==============================
# MOVIE / SERIES DETAILS
# ==============================

@app.route("/movie/<int:movie_id>")
def movie(movie_id):

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    # ------------------------------
    # Get series/movie information
    # ------------------------------

    details_url = f"https://api.themoviedb.org/3/tv/{movie_id}"

    details_params = {
        "language": "en-US"
    }

    details_response = requests.get(
        details_url,
        headers=headers,
        params=details_params,
        timeout=10
    )

    movie_data = details_response.json()


    # ------------------------------
    # Get cast information
    # ------------------------------

    credits_url = f"https://api.themoviedb.org/3/tv/{movie_id}/credits"

    credits_params = {
        "language": "en-US"
    }

    credits_response = requests.get(
        credits_url,
        headers=headers,
        params=credits_params,
        timeout=10
    )

    credits_data = credits_response.json()

    cast = credits_data.get("cast", [])


    # ------------------------------
    # Send everything to HTML
    # ------------------------------

    return render_template(
        "movie_details.html",
        movie=movie_data,
        cast=cast
    )


# ==============================
# RUN FLASK
# ==============================
# ==============================
# TMDB SEARCH
# ==============================

@app.route("/search")
def search():

    query = request.args.get("query", "").strip()

    if not query:
        return redirect(url_for("home"))

    url = "https://api.themoviedb.org/3/search/multi"

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    params = {
        "query": query,
        "language": "en-US",
        "include_adult": False
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10
    )

    search_data = response.json()

    results = []

    for item in search_data.get("results", []):

        # Only movies and TV series
        if item.get("media_type") in ["movie", "tv"]:
            results.append(item)

    return render_template(
        "search_results.html",
        results=results,
        query=query
    )
    # ==============================
# WATCHLIST
# ==============================

@app.route("/watchlist")
def watchlist():

    conn = get_db()

    movies = conn.execute(
        "SELECT * FROM watchlist"
    ).fetchall()

    conn.close()

    return render_template(
        "watchlist.html",
        movies=movies
    )


# ==============================
# ADD TO WATCHLIST
# ==============================

@app.route("/add-to-watchlist/<int:movie_id>")
def add_to_watchlist(movie_id):

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    url = f"https://api.themoviedb.org/3/tv/{movie_id}"

    response = requests.get(
        url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )

    movie = response.json()

    conn = get_db()

    conn.execute(
        """
        INSERT OR IGNORE INTO watchlist
        (movie_id, title, poster_path)
        VALUES (?, ?, ?)
        """,
        (
            movie_id,
            movie.get("name"),
            movie.get("poster_path")
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("movie", movie_id=movie_id))


# ==============================
# REMOVE FROM WATCHLIST
# ==============================

@app.route("/remove-from-watchlist/<int:movie_id>")
def remove_from_watchlist(movie_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM watchlist WHERE movie_id = ?",
        (movie_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("watchlist"))
# ==============================
# COMPLETED PAGE
# ==============================

@app.route("/completed")
def completed():

    conn = get_db()

    movies = conn.execute(
        "SELECT * FROM completed"
    ).fetchall()

    conn.close()

    return render_template(
        "completed.html",
        movies=movies
    )


# ==============================
# ADD TO COMPLETED
# ==============================

@app.route("/add-to-completed/<int:movie_id>")
def add_to_completed(movie_id):

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    url = f"https://api.themoviedb.org/3/tv/{movie_id}"

    response = requests.get(
        url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )

    movie = response.json()

    conn = get_db()

    conn.execute(
        """
        INSERT OR IGNORE INTO completed
        (movie_id, title, poster_path)
        VALUES (?, ?, ?)
        """,
        (
            movie_id,
            movie.get("name"),
            movie.get("poster_path")
        )
    )

    conn.execute(
        "DELETE FROM watchlist WHERE movie_id = ?",
        (movie_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("completed"))


# ==============================
# REMOVE FROM COMPLETED
# ==============================

@app.route("/remove-from-completed/<int:movie_id>")
def remove_from_completed(movie_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM completed WHERE movie_id = ?",
        (movie_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("completed"))
if __name__ == "__main__":
    app.run(debug=True)