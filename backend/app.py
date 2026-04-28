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
