from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pickle
import requests
import os
from dotenv import load_dotenv
import gdown

# Load environment variables
load_dotenv()
WATCHMODE_API_KEY = os.getenv("WATCHMODE_API_KEY")

app = FastAPI()
movies = pickle.load(open('movies.pkl', "rb"))
similarity = pickle.load(open('similarity.pkl', "rb"))

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cache to avoid repeated API calls
movie_cache = {}


# ------------------ Recommendation Logic ------------------ #
def recommend(movie):
    if movie not in movies['title'].values:
        return []

    index = movies[movies['title'] == movie].index[0]
    distances = similarity[index]
    movies_list = sorted(list(enumerate(distances)),
                         key=lambda x: x[1], reverse=True)[1:11]

    return [movies.iloc[i[0]].title for i in movies_list]


# ------------------ Routes ------------------ #
@app.get("/")
def home():
    return {"message": "Movie Recommender API is running"}


@app.get("/movies")
def get_movies():
    return movies["title"].tolist()


@app.get("/recommend/{movie}")
def get_recommendations(movie: str):
    return recommend(movie)


# ------------------ Movie Details (Watchmode) ------------------ #
@app.get("/movie_details/{movie_name}")
def movie_details(movie_name: str):

    if movie_name in movie_cache:
        return movie_cache[movie_name]

    # Step 1: Search movie by title
    search_url = f"https://api.watchmode.com/v1/search/?apiKey={WATCHMODE_API_KEY}&search_field=name&search_value={movie_name}"
    search_res = requests.get(search_url).json()

    if not search_res.get("title_results"):
        return {"error": "Movie not found"}

    movie_id = search_res["title_results"][0]["id"]

    # Step 2: Get full movie details
    details_url = f"https://api.watchmode.com/v1/title/{movie_id}/details/?apiKey={WATCHMODE_API_KEY}"
    data = requests.get(details_url).json()

    # --- FIXED GENRE HANDLING ---
    genre_names = data.get("genre_names") or data.get("genres") or []
    if isinstance(genre_names, list):
        genre_names = [str(g) for g in genre_names]
    else:
        genre_names = []

    movie_data = {
        "title": data.get("title"),
        "year": data.get("year"),
        "genre": ", ".join(genre_names) if genre_names else "N/A",
        "rating": data.get("user_rating") or 0,
        "plot": data.get("plot_overview") or "No plot available",
        "poster": data.get("poster") or None
    }

    movie_cache[movie_name] = movie_data
    return movie_data

import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
