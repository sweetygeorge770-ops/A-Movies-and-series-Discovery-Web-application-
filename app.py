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

    try:
        # Create the new table structures
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL,
                title TEXT,
                poster_path TEXT,
                media_type TEXT NOT NULL DEFAULT 'tv',
                UNIQUE(movie_id, media_type)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS completed_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL,
                title TEXT,
                poster_path TEXT,
                media_type TEXT NOT NULL DEFAULT 'tv',
                UNIQUE(movie_id, media_type)
            )
        """)

        # Copy existing records into the new tables
        for table in ("watchlist", "completed"):
            old_columns = [
                row["name"]
                for row in conn.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            ]

            if table == "watchlist":
                new_table = "watchlist_new"
            else:
                new_table = "completed_new"

            if "media_type" in old_columns:
                conn.execute(f"""
                    INSERT OR IGNORE INTO {new_table}
                    (id, movie_id, title, poster_path, media_type)
                    SELECT id, movie_id, title, poster_path, media_type
                    FROM {table}
                """)
            else:
                conn.execute(f"""
                    INSERT OR IGNORE INTO {new_table}
                    (id, movie_id, title, poster_path, media_type)
                    SELECT id, movie_id, title, poster_path, 'tv'
                    FROM {table}
                """)

        # Replace the old tables
        conn.execute("DROP TABLE watchlist")
        conn.execute("DROP TABLE completed")

        conn.execute("ALTER TABLE watchlist_new RENAME TO watchlist")
        conn.execute("ALTER TABLE completed_new RENAME TO completed")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
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
    trending = get_tmdb_data(
    "https://api.themoviedb.org/3/trending/all/day"
)

    india_movies = get_tmdb_data(
        "https://api.themoviedb.org/3/discover/movie?with_origin_country=IN&sort_by=popularity.desc"
    )

    global_movies = get_tmdb_data(
        "https://api.themoviedb.org/3/movie/popular"
    )
    return render_template(
        "index.html",
        india_movies=india_movies.get("results", []),
        global_movies=global_movies.get("results", []),
        trending=trending.get("results", [])
    )

# ==============================
# MOVIE / SERIES DETAILS
# ==============================

@app.route("/movie/<int:movie_id>")
def movie(movie_id):
    media_type = request.args.get("type", "tv")

    if media_type not in ("movie", "tv"):
        media_type = "tv"

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    details_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}"

    details_response = requests.get(
        details_url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )
    details_response.raise_for_status()
    movie_data = details_response.json()

    credits_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}/credits"

    credits_response = requests.get(
        credits_url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )
    credits_response.raise_for_status()
    cast = credits_response.json().get("cast", [])

    return render_template(
        "movie_details.html",
        movie=movie_data,
        cast=cast,
        movie_id=movie_id,
        media_type=media_type
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

    media_type = request.args.get("type", "tv")

    if media_type not in ("movie", "tv"):
        media_type = "tv"

    url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}"

    response = requests.get(
        url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )

    response.raise_for_status()
    movie = response.json()

    conn = get_db()

    try:
        # Remove from Completed first
        conn.execute(
            "DELETE FROM completed WHERE movie_id = ?",
            (movie_id,)
        )

        # Add to Watchlist if not already present
        conn.execute(
            """
            INSERT OR IGNORE INTO watchlist
            (movie_id, title, poster_path)
            VALUES (?, ?, ?)
            """,
            (
                movie_id,
                movie.get("name") or movie.get("title"),
                movie.get("poster_path")
            )
        )
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return redirect(url_for("movie", movie_id=movie_id, type=media_type))


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

    media_type = request.args.get("type", "tv")

    if media_type not in ("movie", "tv"):
        media_type = "tv"

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}"

    response = requests.get(
        url,
        headers=headers,
        params={"language": "en-US"},
        timeout=10
    )

    response.raise_for_status()
    movie = response.json()

    conn = get_db()

    try:
        # Remove the movie from Watchlist
        conn.execute(
            "DELETE FROM watchlist WHERE movie_id = ?",
            (movie_id,)
        )

        # Add the movie to Completed
        conn.execute(
            """
            INSERT OR IGNORE INTO completed
            (movie_id, title, poster_path)
            VALUES (?, ?, ?)
            """,
            (
                movie_id,
                movie.get("name") or movie.get("title"),
                movie.get("poster_path")
            )
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
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