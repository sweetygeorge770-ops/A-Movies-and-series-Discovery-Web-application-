from flask import Flask, render_template, redirect, url_for, request
import requests
from dotenv import dotenv_values

config = dotenv_values(".env")

app = Flask(__name__)

TMDB_TOKEN = config.get("TMDB_TOKEN")


# ==============================
# HOME PAGE
# ==============================

@app.route("/")
def home():
    return render_template("index.html")


# ==============================
# OLD MOVIE LINK
# ==============================
# Your current Wednesday card uses /movie
# So this redirects it to Wednesday's TMDB page.

@app.route("/movie")
def movie_default():
    return redirect(url_for("movie", movie_id=119051))


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
if __name__ == "__main__":
    app.run(debug=True)