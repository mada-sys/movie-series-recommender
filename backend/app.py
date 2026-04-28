from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
DATABASE_NAME = "database.db"

TMDB_BEARER_TOKEN = "PASTE_YOUR_TMDB_TOKEN_HERE"
#TMDB_BEARER_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI2NmE4ZWJlZGNmMzI2YzQ2ODc1M2NkNzdiZjNkMmQyYSIsIm5iZiI6MTc3Njc3ODk5MC45NTEsInN1YiI6IjY5ZTc3ZWVlYWI3NmUxZjYyOTkzOTk5MCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.agdvloPAvIYNvC57NNlGHnGwWsvJ_DYytc6VleLqXb8"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
MEDIA_DETAILS_CACHE = {}

ITEMS_PER_PAGE = 10
TMDB_PAGES_PER_BATCH = 3
MOVIE_GENRE_MAP = {
    "Action": 28,
    "Comedy": 35,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Drama": 18,
    "Thriller": 53,
    "Mystery": 9648,
    "Fantasy": 14,
    "Adventure": 12,
    "Crime": 80,
    "Animation": 16,
    "Horror": 27
}

# TMDB uses different IDs for TV. Some movie genres do not exist for TV,
# so we map them to the closest available TV genre.
TV_GENRE_MAP = {
    "Action": 10759,       # Action & Adventure
    "Adventure": 10759,    # Action & Adventure
    "Comedy": 35,
    "Romance": 18,         # no direct TV genre → Drama
    "Sci-Fi": 10765,       # Sci-Fi & Fantasy
    "Fantasy": 10765,      # Sci-Fi & Fantasy
    "Drama": 18,
    "Thriller": 9648,      # no direct TV genre → Mystery
    "Mystery": 9648,
    "Crime": 80,
    "Animation": 16,
    "Horror": 9648         # no direct TV genre → Mystery
}

LANGUAGE_MAP = {
    "English": "en",
    "French": "fr",
    "Spanish": "es"
}

DURATION_MAP = {
    "Short": (0, 95),
    "Medium": (96, 125),
    "Long": (126, 400)
}

MOVIE_MOOD_BONUS_GENRES = {
    "Intense": [28, 53, 80, 878, 12],
    "Dark": [53, 80, 27, 9648],
    "Emotional": [18, 10749, 10751],
    "Fun": [35, 12, 16]
}

TV_MOOD_BONUS_GENRES = {
    "Intense": [10759, 80, 9648, 10765],
    "Dark": [80, 9648, 10768],
    "Emotional": [18, 10751],
    "Fun": [35, 16, 10762]
}
# Maps the user's mood profile cluster to the movie/TV genre names that
# should receive a bonus. The scoring function looks up the right ID map
# for the requested content type.
MOOD_PROFILE_TO_GENRES = {
    "intense_and_dark": ["Thriller", "Crime", "Action", "Horror"],
    "emotional_and_reflective": ["Drama", "Romance"],
    "cerebral_and_mysterious": ["Mystery", "Sci-Fi", "Thriller"],
    "imaginative_and_exploratory": ["Sci-Fi", "Fantasy", "Adventure"],
    "light_and_feel_good": ["Comedy", "Animation", "Romance"]
}

MOOD_PROFILE_REASONS = {
    "intense_and_dark": "fits your intense / dark personality profile",
    "emotional_and_reflective": "fits your emotional / reflective personality profile",
    "cerebral_and_mysterious": "fits your cerebral / mysterious personality profile",
    "imaginative_and_exploratory": "fits your imaginative / exploratory personality profile",
    "light_and_feel_good": "fits your light / feel-good personality profile"
}
