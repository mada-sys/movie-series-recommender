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
PERSONALITY_QUESTIONS = [
    {
        "id": "q1",
        "question": "How do you prefer to spend an ideal weekend?",
        "options": {
            "A": "At home, quietly, with time for myself",
            "B": "With a few close friends",
            "C": "Going out and exploring new places",
            "D": "At a big event with lots of energy"
        }
    },
    {
        "id": "q2",
        "question": "When an unexpected problem appears, how do you usually react?",
        "options": {
            "A": "I analyze it calmly before doing anything",
            "B": "I ask for a second opinion",
            "C": "I act quickly in the moment",
            "D": "I step back and process it alone"
        }
    },
    {
        "id": "q3",
        "question": "What attracts you the most in a story?",
        "options": {
            "A": "The emotions of the characters",
            "B": "Its logic and structure",
            "C": "Suspense and plot twists",
            "D": "Atmosphere and visual style"
        }
    },
    {
        "id": "q4",
        "question": "How often do you actively seek new experiences?",
        "options": {
            "A": "Rarely, I prefer what I already know",
            "B": "Sometimes, if it looks interesting",
            "C": "Often, I like variety",
            "D": "Very often, I get bored quickly"
        }
    },
    {
        "id": "q5",
        "question": "Which atmosphere represents you best?",
        "options": {
            "A": "Cozy, warm, comfortable",
            "B": "Melancholic and deep",
            "C": "Energetic and dynamic",
            "D": "Mysterious and slightly dark"
        }
    },
    {
        "id": "q6",
        "question": "In relationships with others, you consider yourself more:",
        "options": {
            "A": "Reserved and observant",
            "B": "Empathetic and emotionally close",
            "C": "Direct and decisive",
            "D": "Sociable and expressive"
        }
    },
    {
        "id": "q7",
        "question": "When choosing something for relaxation, you prefer:",
        "options": {
            "A": "Something calm and predictable",
            "B": "Something emotional and memorable",
            "C": "Something fast-paced and gripping",
            "D": "Something strange, different, unusual"
        }
    },
    {
        "id": "q8",
        "question": "How comfortable are you with ambiguous endings?",
        "options": {
            "A": "Not at all, I want clear conclusions",
            "B": "A little, if the rest is good",
            "C": "Quite comfortable",
            "D": "Very comfortable, I even enjoy them"
        }
    },
    {
        "id": "q9",
        "question": "What matters most to you in a great experience?",
        "options": {
            "A": "It makes me feel something deeply",
            "B": "It keeps me on edge",
            "C": "It makes me think",
            "D": "It puts me in a good mood"
        }
    },
    {
        "id": "q10",
        "question": "How would you describe yourself best?",
        "options": {
            "A": "Calm and balanced",
            "B": "Sensitive and introspective",
            "C": "Curious and imaginative",
            "D": "Energetic and impulsive"
        }
    },
    {
        "id": "q11",
        "question": "How much do you enjoy intense experiences?",
        "options": {
            "A": "Very little",
            "B": "Moderately",
            "C": "A lot",
            "D": "Very much"
        }
    },
    {
        "id": "q12",
        "question": "What kind of world attracts you more?",
        "options": {
            "A": "A realistic one, close to everyday life",
            "B": "A romantic or idealized one",
            "C": "A tense, hard, unpredictable one",
            "D": "A fantastic, futuristic or unusual one"
        }
    },
    {
        "id": "q13",
        "question": "If something stays with you for a long time, it is usually because:",
        "options": {
            "A": "It moved me deeply",
            "B": "It surprised me intellectually",
            "C": "It shocked or intensely stressed me",
            "D": "It inspired me or gave me a special feeling"
        }
    },
    {
        "id": "q14",
        "question": "You prefer experiences that:",
        "options": {
            "A": "Confirm your tastes and comfort zone",
            "B": "Stay near your taste, with small surprises",
            "C": "Sometimes push you out of your comfort zone",
            "D": "Surprise you completely"
        }
    },
    {
        "id": "q15",
        "question": "If you had to choose one direction that represents you right now, it would be:",
        "options": {
            "A": "Emotional connection",
            "B": "Adrenaline and intensity",
            "C": "Introspection and depth",
            "D": "Escape and imagination"
        }
    }
]

PERSONALITY_DIMENSION_RULES = {
    "q1": {
        "A": {"comfort": 2, "introspection": 2},
        "B": {"social": 2, "emotion": 1, "comfort": 1},
        "C": {"curiosity": 2, "adventure": 2, "energy": 1},
        "D": {"social": 2, "energy": 2, "intensity": 1}
    },
    "q2": {
        "A": {"logic": 2, "comfort": 1},
        "B": {"social": 2, "emotion": 1},
        "C": {"energy": 2, "intensity": 2},
        "D": {"introspection": 2, "logic": 1}
    },
    "q3": {
        "A": {"emotion": 2, "introspection": 1},
        "B": {"logic": 2, "realism": 1},
        "C": {"suspense": 2, "intensity": 1},
        "D": {"imagination": 2, "darkness": 1}
    },
    "q4": {
        "A": {"comfort": 2},
        "B": {"curiosity": 1},
        "C": {"curiosity": 2, "adventure": 1},
        "D": {"curiosity": 3, "adventure": 2}
    },
    "q5": {
        "A": {"comfort": 2},
        "B": {"emotion": 2, "introspection": 1},
        "C": {"energy": 2, "intensity": 1},
        "D": {"darkness": 2, "ambiguity": 1}
    },
    "q6": {
        "A": {"introspection": 2},
        "B": {"emotion": 2, "social": 1},
        "C": {"intensity": 1, "logic": 1, "energy": 1},
        "D": {"social": 2, "energy": 1}
    },
    "q7": {
        "A": {"comfort": 2},
        "B": {"emotion": 2},
        "C": {"intensity": 2, "suspense": 1},
        "D": {"curiosity": 2, "imagination": 1, "ambiguity": 1}
    },
    "q8": {
        "A": {"comfort": 2, "realism": 1},
        "B": {"ambiguity": 1},
        "C": {"ambiguity": 2},
        "D": {"ambiguity": 3, "curiosity": 1}
    },
    "q9": {
        "A": {"emotion": 2},
        "B": {"intensity": 2, "suspense": 1},
        "C": {"logic": 1, "introspection": 2},
        "D": {"comfort": 1, "social": 1}
    },
    "q10": {
        "A": {"comfort": 2, "logic": 1},
        "B": {"emotion": 2, "introspection": 2},
        "C": {"curiosity": 2, "imagination": 2},
        "D": {"energy": 2, "intensity": 2}
    },
    "q11": {
        "A": {"comfort": 2},
        "B": {"intensity": 1},
        "C": {"intensity": 2, "energy": 1},
        "D": {"intensity": 3, "darkness": 1}
    },
    "q12": {
        "A": {"realism": 2},
        "B": {"emotion": 2, "comfort": 1},
        "C": {"darkness": 2, "intensity": 1, "realism": 1},
        "D": {"imagination": 3, "curiosity": 1}
    },
    "q13": {
        "A": {"emotion": 2},
        "B": {"logic": 2, "ambiguity": 1},
        "C": {"intensity": 2, "darkness": 2},
        "D": {"imagination": 1, "introspection": 1, "emotion": 1}
    },
    "q14": {
        "A": {"comfort": 2},
        "B": {"comfort": 1, "curiosity": 1},
        "C": {"curiosity": 2},
        "D": {"curiosity": 3, "ambiguity": 1, "adventure": 1}
    },
    "q15": {
        "A": {"emotion": 2, "social": 1},
        "B": {"intensity": 2, "energy": 1},
        "C": {"introspection": 2, "logic": 1},
        "D": {"imagination": 2, "adventure": 1}
    }
}
DIMENSION_LABELS = {
    "comfort": "comfort-seeking",
    "emotion": "emotionally driven",
    "introspection": "introspective",
    "social": "socially oriented",
    "curiosity": "curious",
    "energy": "high-energy",
    "intensity": "intensity-seeking",
    "darkness": "dark / mysterious",
    "imagination": "imaginative",
    "realism": "realism-oriented",
    "ambiguity": "ambiguity-tolerant",
    "suspense": "suspense-oriented",
    "logic": "analytical",
    "adventure": "adventure-seeking"
}
# =========================
# DATABASE
# =========================
def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personality_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            q1 TEXT NOT NULL,
            q2 TEXT NOT NULL,
            q3 TEXT NOT NULL,
            q4 TEXT NOT NULL,
            q5 TEXT NOT NULL,
            q6 TEXT NOT NULL,
            q7 TEXT NOT NULL,
            q8 TEXT NOT NULL,
            q9 TEXT NOT NULL,
            q10 TEXT NOT NULL,
            q11 TEXT NOT NULL,
            q12 TEXT NOT NULL,
            q13 TEXT NOT NULL,
            q14 TEXT NOT NULL,
            q15 TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


init_db()
# =========================
# GENERIC HELPERS
# =========================
def get_tmdb_headers():
    return {
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
        "accept": "application/json"
    }


def build_image_url(path):
    if not path:
        return None
    return f"{TMDB_IMAGE_BASE_URL}{path}"


def normalize_answer(value):
    if value is None:
        return None
    return str(value).strip().upper()


def user_exists(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user is not None


def user_has_personality_test(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM personality_tests WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_personality_test_row(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM personality_tests WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def row_to_answers(row):
    if row is None:
        return None
    return {f"q{i}": row[f"q{i}"] for i in range(1, 16)}


def extract_answers_from_payload(payload):
    answers = payload.get("answers")

    if isinstance(answers, dict):
        return {f"q{i}": normalize_answer(answers.get(f"q{i}")) for i in range(1, 16)}

    return {f"q{i}": normalize_answer(payload.get(f"q{i}")) for i in range(1, 16)}


def validate_personality_answers(answers):
    missing = []
    invalid = []

    for i in range(1, 16):
        key = f"q{i}"
        value = answers.get(key)

        if not value:
            missing.append(key)
        elif value not in {"A", "B", "C", "D"}:
            invalid.append(key)

    return missing, invalid


def save_or_update_personality_test(user_id, answers):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM personality_tests WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    values = [answers[f"q{i}"] for i in range(1, 16)]

    if existing:
        cursor.execute("""
            UPDATE personality_tests
            SET
                q1 = ?, q2 = ?, q3 = ?, q4 = ?, q5 = ?,
                q6 = ?, q7 = ?, q8 = ?, q9 = ?, q10 = ?,
                q11 = ?, q12 = ?, q13 = ?, q14 = ?, q15 = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (*values, user_id))
    else:
        cursor.execute("""
            INSERT INTO personality_tests (
                user_id, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13, q14, q15
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, *values))

    conn.commit()
    conn.close()


def delete_personality_test(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM personality_tests WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
# =========================
# PERSONALITY PROFILE
# =========================
def get_discovery_level(dimensions):
    exploration_score = dimensions["curiosity"] + dimensions["ambiguity"] + dimensions["adventure"]
    comfort_score = dimensions["comfort"]

    if exploration_score >= comfort_score + 4:
        return "High"
    if exploration_score >= comfort_score + 1:
        return "Medium"
    return "Low"


def get_intensity_level(dimensions):
    score = dimensions["intensity"] + dimensions["energy"]
    calm_score = dimensions["comfort"]

    if score >= calm_score + 4:
        return "High"
    if score >= calm_score + 1:
        return "Medium"
    return "Low"


def get_social_style(dimensions):
    if dimensions["social"] >= dimensions["introspection"] + 2:
        return "Social"
    if dimensions["introspection"] >= dimensions["social"] + 2:
        return "Introspective"
    return "Balanced"


def get_mood_profile(dimensions):
    cluster_scores = {
        "light_and_feel_good": dimensions["comfort"] + dimensions["social"] + dimensions["emotion"] * 0.5,
        "emotional_and_reflective": dimensions["emotion"] + dimensions["introspection"],
        "intense_and_dark": dimensions["intensity"] + dimensions["darkness"] + dimensions["suspense"],
        "cerebral_and_mysterious": dimensions["logic"] + dimensions["ambiguity"] + dimensions["curiosity"] * 0.5,
        "imaginative_and_exploratory": dimensions["imagination"] + dimensions["curiosity"] + dimensions["adventure"]
    }

    mood_key = max(cluster_scores, key=cluster_scores.get)
    mood_labels = {
        "light_and_feel_good": "Light and feel-good",
        "emotional_and_reflective": "Emotional and reflective",
        "intense_and_dark": "Intense and dark",
        "cerebral_and_mysterious": "Cerebral and mysterious",
        "imaginative_and_exploratory": "Imaginative and exploratory"
    }

    return mood_key, mood_labels[mood_key]


def build_genre_scores(dimensions):
    raw_scores = {
        "Drama": dimensions["emotion"] * 1.5 + dimensions["introspection"] * 1.3 + dimensions["realism"] * 0.7,
        "Romance": dimensions["emotion"] * 1.3 + dimensions["comfort"] * 0.8 + dimensions["social"] * 0.6,
        "Comedy": max(0, dimensions["comfort"] * 1.4 + dimensions["social"] * 0.8 + dimensions["energy"] * 0.4 - dimensions["darkness"] * 0.2),
        "Action": dimensions["intensity"] * 1.4 + dimensions["energy"] * 1.2 + dimensions["adventure"] * 0.8,
        "Thriller": dimensions["suspense"] * 1.5 + dimensions["darkness"] * 1.1 + dimensions["intensity"] * 0.7,
        "Mystery": dimensions["ambiguity"] * 1.4 + dimensions["logic"] * 1.0 + dimensions["suspense"] * 0.7,
        "Sci-Fi": dimensions["imagination"] * 1.4 + dimensions["curiosity"] * 1.2 + dimensions["logic"] * 0.7,
        "Fantasy": dimensions["imagination"] * 1.3 + dimensions["adventure"] * 1.0 + dimensions["comfort"] * 0.4,
        "Adventure": dimensions["adventure"] * 1.4 + dimensions["curiosity"] * 1.0 + dimensions["energy"] * 0.8,
        "Crime": dimensions["darkness"] * 0.9 + dimensions["suspense"] * 0.9 + dimensions["realism"] * 0.8,
        "Animation": dimensions["comfort"] * 0.9 + dimensions["imagination"] * 0.8 + dimensions["emotion"] * 0.4,
        "Horror": dimensions["darkness"] * 1.4 + dimensions["intensity"] * 0.9 + dimensions["suspense"] * 1.0
    }

    return dict(sorted(raw_scores.items(), key=lambda item: item[1], reverse=True))


def build_personality_profile(answers):
    dimensions = {
        "comfort": 0,
        "emotion": 0,
        "introspection": 0,
        "social": 0,
        "curiosity": 0,
        "energy": 0,
        "intensity": 0,
        "darkness": 0,
        "imagination": 0,
        "realism": 0,
        "ambiguity": 0,
        "suspense": 0,
        "logic": 0,
        "adventure": 0
    }

    for question_id, option_map in PERSONALITY_DIMENSION_RULES.items():
        answer = answers.get(question_id)
        if answer in option_map:
            for dimension, value in option_map[answer].items():
                dimensions[dimension] += value

    sorted_dimensions = sorted(dimensions.items(), key=lambda item: item[1], reverse=True)
    top_traits = [
        {
            "key": key,
            "label": DIMENSION_LABELS.get(key, key),
            "score": score
        }
        for key, score in sorted_dimensions[:4]
    ]

    genre_scores_raw = build_genre_scores(dimensions)
    recommended_genres = list(genre_scores_raw.keys())[:4]

    mood_key, mood_label = get_mood_profile(dimensions)

    profile = {
        "dimensions": dimensions,
        "top_traits": top_traits,
        "recommended_genres": recommended_genres,
        "genre_scores_raw": genre_scores_raw,
        "mood_profile_key": mood_key,
        "mood_profile_label": mood_label,
        "discovery_level": get_discovery_level(dimensions),
        "intensity_level": get_intensity_level(dimensions),
        "social_style": get_social_style(dimensions)
    }

    return profile


def serialize_profile(profile):
    return {
        "top_traits": profile["top_traits"],
        "recommended_genres": profile["recommended_genres"],
        "mood_profile_label": profile["mood_profile_label"],
        "discovery_level": profile["discovery_level"],
        "intensity_level": profile["intensity_level"],
        "social_style": profile["social_style"],
        "dimensions": profile["dimensions"]
    }


def enrich_match_percentages(items):
    if not items:
        return items

    max_score = max(item.get("score", 0) for item in items) or 1

    for item in items:
        raw_score = item.get("score", 0)
        item["match_percentage"] = round((raw_score / max_score) * 100)

    return items
# =========================
# CONTENT TYPE HELPERS
# =========================
def normalize_content_type(value):
    if value is None:
        return "movie"
    value = str(value).strip().lower()
    if value in ("tv", "series", "show", "shows"):
        return "tv"
    return "movie"


def get_genre_map(content_type):
    if content_type == "tv":
        return TV_GENRE_MAP
    return MOVIE_GENRE_MAP


def get_mood_bonus_genres(mood, content_type):
    if content_type == "tv":
        return TV_MOOD_BONUS_GENRES.get(mood, [])
    return MOVIE_MOOD_BONUS_GENRES.get(mood, [])


def get_discover_endpoint(content_type):
    if content_type == "tv":
        return f"{TMDB_BASE_URL}/discover/tv"
    return f"{TMDB_BASE_URL}/discover/movie"


def get_tmdb_pages_for_app_page(app_page, pages_per_batch=TMDB_PAGES_PER_BATCH):
    start = (app_page - 1) * pages_per_batch + 1
    return list(range(start, start + pages_per_batch))


def parse_app_page(value, default=1):
    try:
        page = int(value)
    except (TypeError, ValueError):
        return default
    return page if page >= 1 else default
# =========================
# TMDB FETCHERS
# =========================
def discover_items(selected_genre, selected_language, selected_duration, content_type, tmdb_pages):
    genre_map = get_genre_map(content_type)
    genre_id = genre_map.get(selected_genre)
    language_code = LANGUAGE_MAP.get(selected_language)
    runtime_range = DURATION_MAP.get(selected_duration)

    endpoint = get_discover_endpoint(content_type)

    all_items = []
    seen_ids = set()
    max_available_page = 0

    for page in tmdb_pages:
        # Note: TMDB returns results sorted by popularity. We still re-sort
        # locally by our own score after formatting.
        params = {
            "language": "en-US",
            "include_adult": "false",
            "sort_by": "popularity.desc",
            "page": page,
            "vote_count.gte": 200
        }

        if content_type == "movie":
            params["include_video"] = "false"

        if genre_id:
            params["with_genres"] = genre_id

        if language_code:
            params["with_original_language"] = language_code

        # Runtime filter only exists for movies on TMDB discover.
        if content_type == "movie" and runtime_range:
            params["with_runtime.gte"] = runtime_range[0]
            params["with_runtime.lte"] = runtime_range[1]

        response = requests.get(
            endpoint,
            headers=get_tmdb_headers(),
            params=params,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()
        max_available_page = max(max_available_page, data.get("total_pages", 0))

        for item in data.get("results", []):
            item_id = item.get("id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                all_items.append(item)

    return all_items, max_available_page


def discover_items_by_personality(profile, content_type, app_page):
    genre_map = get_genre_map(content_type)
    endpoint = get_discover_endpoint(content_type)

    all_items = []
    seen_ids = set()
    any_has_more = False

    for genre_name in profile["recommended_genres"][:3]:
        genre_id = genre_map.get(genre_name)
        if not genre_id:
            continue

        params = {
            "language": "en-US",
            "include_adult": "false",
            "sort_by": "popularity.desc",
            "page": app_page,
            "vote_count.gte": 200,
            "with_genres": genre_id
        }

        if content_type == "movie":
            params["include_video"] = "false"

        response = requests.get(
            endpoint,
            headers=get_tmdb_headers(),
            params=params,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()
        total_pages = data.get("total_pages", 0)

        if total_pages > app_page:
            any_has_more = True

        for item in data.get("results", []):
            item_id = item.get("id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                all_items.append(item)

    return all_items, any_has_more


def pick_trailer_video(videos):
    youtube_candidates = [
        video for video in videos
        if video.get("site") == "YouTube" and video.get("key")
    ]

    if not youtube_candidates:
        return {}

    youtube_candidates.sort(
        key=lambda video: (
            0 if video.get("type") == "Trailer" else 1,
            0 if video.get("official") else 1,
            -(video.get("size") or 0)
        )
    )

    trailer = youtube_candidates[0]
    trailer_key = trailer.get("key")

    return {
        "trailer_name": trailer.get("name"),
        "trailer_url": f"https://www.youtube.com/watch?v={trailer_key}",
        "trailer_embed_url": f"https://www.youtube.com/embed/{trailer_key}?rel=0"
    }


def get_media_details(item_id, content_type):
    if not item_id:
        return {}

    cache_key = f"{content_type}-{item_id}"
    if cache_key in MEDIA_DETAILS_CACHE:
        return MEDIA_DETAILS_CACHE[cache_key]

    try:
        response = requests.get(
            f"{TMDB_BASE_URL}/{content_type}/{item_id}",
            headers=get_tmdb_headers(),
            params={
                "language": "en-US",
                "append_to_response": "videos"
            },
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        details = pick_trailer_video(data.get("videos", {}).get("results", []))

        if content_type == "movie":
            details["runtime_minutes"] = data.get("runtime")

        if content_type == "tv":
            details["number_of_seasons"] = data.get("number_of_seasons")
            details["number_of_episodes"] = data.get("number_of_episodes")
    except requests.exceptions.RequestException:
        details = {}

    MEDIA_DETAILS_CACHE[cache_key] = details
    return details
# =========================
# SCORING
# =========================
def score_item(item, selected_genre, selected_mood, selected_duration, selected_language, content_type):
    score = 0
    reasons = []

    genre_ids = item.get("genre_ids", [])
    original_language = item.get("original_language")
    vote_average = item.get("vote_average") or 0
    popularity = item.get("popularity") or 0

    genre_map = get_genre_map(content_type)
    selected_genre_id = genre_map.get(selected_genre)
    selected_language_code = LANGUAGE_MAP.get(selected_language)
    mood_bonus_genres = get_mood_bonus_genres(selected_mood, content_type)

    if selected_genre_id and selected_genre_id in genre_ids:
        score += 5
        reasons.append("matches your selected genre")

    if any(genre_id in genre_ids for genre_id in mood_bonus_genres):
        score += 3
        reasons.append("fits your selected mood")

    if selected_language_code and original_language == selected_language_code:
        score += 2
        reasons.append("matches your preferred language")

    # Duration only applies for movies - TV doesn't return runtime from discover.
    if content_type == "movie" and selected_duration in DURATION_MAP:
        score += 2
        reasons.append("fits your preferred duration")

    if vote_average >= 7.5:
        score += 2
        reasons.append("has a strong rating")
    elif vote_average >= 6.5:
        score += 1

    if popularity >= 100:
        score += 1
        reasons.append("is popular on TMDb")

    return score, reasons


def score_item_by_personality(item, profile, content_type):
    score = 0
    reasons = []

    genre_ids = item.get("genre_ids", [])
    vote_average = item.get("vote_average") or 0
    popularity = item.get("popularity") or 0

    genre_map = get_genre_map(content_type)
    genre_scores_raw = profile["genre_scores_raw"]

    matched_genres = []
    for genre_name in profile["recommended_genres"][:5]:
        genre_id = genre_map.get(genre_name)
        if genre_id and genre_id in genre_ids:
            matched_genres.append(genre_name)
            score += genre_scores_raw.get(genre_name, 0)

    mood_key = profile["mood_profile_key"]
    mood_genre_names = MOOD_PROFILE_TO_GENRES.get(mood_key, [])
    mood_genre_ids = [genre_map[name] for name in mood_genre_names if name in genre_map]

    if any(g in genre_ids for g in mood_genre_ids):
        score += 4
        reasons.append(MOOD_PROFILE_REASONS[mood_key])

    if matched_genres:
        reasons.append(f"aligned genres: {', '.join(matched_genres[:3])}")

    if vote_average >= 7.5:
        score += 2
        reasons.append("has a strong rating")
    elif vote_average >= 6.5:
        score += 1
# =========================
# FORMATTING
# =========================
def format_item(item, score, reasons, content_type):
    # Normalize TV fields (name / first_air_date) to the same keys movies use,
    # so the frontend can render both with the same component.
    if content_type == "tv":
        title = item.get("name")
        release_date = item.get("first_air_date")
    else:
        title = item.get("title")
        release_date = item.get("release_date")

    return {
        "id": item.get("id"),
        "title": title,
        "overview": item.get("overview") or "No overview available.",
        "poster_path": item.get("poster_path"),
        "poster_url": build_image_url(item.get("poster_path")),
        "backdrop_url": build_image_url(item.get("backdrop_path")),
        "release_date": release_date,
        "vote_average": item.get("vote_average"),
        "vote_count": item.get("vote_count"),
        "popularity": item.get("popularity"),
        "original_language": item.get("original_language"),
        "genre_ids": item.get("genre_ids", []),
        "content_type": content_type,
        "score": score,
        "why_recommended": reasons
    }


def enrich_media_details(items):
    for item in items:
        content_type = item.get("content_type") or "movie"
        details = get_media_details(item.get("id"), content_type)

        item["trailer_name"] = details.get("trailer_name")
        item["trailer_url"] = details.get("trailer_url")
        item["trailer_embed_url"] = details.get("trailer_embed_url")
        item["runtime_minutes"] = details.get("runtime_minutes")
        item["media_details_loaded"] = True

        if content_type == "tv":
            item["number_of_seasons"] = details.get("number_of_seasons")
            item["number_of_episodes"] = details.get("number_of_episodes")


@app.route("/media-details/<content_type>/<int:item_id>", methods=["GET"])
def media_details_route(content_type, item_id):
    try:
        normalized_content_type = normalize_content_type(content_type)
        details = get_media_details(item_id, normalized_content_type)
        details["content_type"] = normalized_content_type
        details["media_details_loaded"] = True
        return jsonify(details), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def sort_scored_items(items):
    items.sort(
        key=lambda m: (
            m["score"],
            m["vote_average"] if m["vote_average"] is not None else 0,
            m["popularity"] if m["popularity"] is not None else 0
        ),
        reverse=True
    )
    return items
    if popularity >= 100:
        score += 1
        reasons.append("is popular on TMDb")

    return round(score, 2), reasons
# =========================
# BASIC ROUTES
# =========================
@app.route("/")
def home():
    return {"message": "Backend running"}


@app.route("/tmdb-test", methods=["GET"])
def tmdb_test():
    try:
        if "PASTE_YOUR_NEW_TMDB_TOKEN_HERE" in TMDB_BEARER_TOKEN:
            return jsonify({"error": "TMDB token is missing."}), 500

        items, _ = discover_items(
            selected_genre="Action",
            selected_language="English",
            selected_duration="Long",
            content_type="movie",
            tmdb_pages=[1]
        )
        preview = []

        for item in items[:5]:
            preview.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "poster_url": build_image_url(item.get("poster_path")),
                "release_date": item.get("release_date"),
                "vote_average": item.get("vote_average")
            })

        return jsonify(preview)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# AUTH ROUTES
# =========================
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(silent=True) or {}

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not username or not email or not password:
            return jsonify({"error": "All fields are required."}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must have at least 6 characters."}), 400

        hashed_password = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_email = cursor.fetchone()

        if existing_email:
            conn.close()
            return jsonify({"error": "An account with this email already exists."}), 400

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_username = cursor.fetchone()

        if existing_username:
            conn.close()
            return jsonify({"error": "This username is already taken."}), 400

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "message": "User registered successfully.",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "has_personality_test": False
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(silent=True) or {}

        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            return jsonify({"error": "Invalid credentials."}), 401

        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid credentials."}), 401

        has_personality_test = user_has_personality_test(user["id"])

        return jsonify({
            "message": "Login successful.",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "has_personality_test": has_personality_test
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# PERSONALITY TEST ROUTES
# =========================
@app.route("/personality-questions", methods=["GET"])
def personality_questions():
    return jsonify(PERSONALITY_QUESTIONS)


@app.route("/personality-test/status/<int:user_id>", methods=["GET"])
def personality_test_status(user_id):
    try:
        if not user_exists(user_id):
            return jsonify({"error": "User not found."}), 404

        row = get_personality_test_row(user_id)

        if row is None:
            return jsonify({
                "has_test": False,
                "completed_at": None,
                "updated_at": None
            }), 200

        return jsonify({
            "has_test": True,
            "completed_at": row["created_at"],
            "updated_at": row["updated_at"]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/personality-test/<int:user_id>", methods=["GET"])
def get_personality_test(user_id):
    try:
        if not user_exists(user_id):
            return jsonify({"error": "User not found."}), 404

        row = get_personality_test_row(user_id)

        if row is None:
            return jsonify({
                "has_test": False,
                "answers": None,
                "profile": None
            }), 200

        answers = row_to_answers(row)
        profile = build_personality_profile(answers)

        return jsonify({
            "has_test": True,
            "answers": answers,
            "profile": serialize_profile(profile),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/personality-test", methods=["POST"])
def save_personality_test_route():
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"error": "user_id is required."}), 400

        if not user_exists(user_id):
            return jsonify({"error": "User not found."}), 404

        answers = extract_answers_from_payload(data)
        missing, invalid = validate_personality_answers(answers)

        if missing:
            return jsonify({
                "error": "All 15 questions must be answered.",
                "missing": missing
            }), 400

        if invalid:
            return jsonify({
                "error": "Some answers are invalid. Allowed values are A, B, C, D.",
                "invalid": invalid
            }), 400

        save_or_update_personality_test(user_id, answers)
        profile = build_personality_profile(answers)

        return jsonify({
            "message": "Personality test saved successfully.",
            "has_test": True,
            "profile": serialize_profile(profile)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/personality-test/<int:user_id>", methods=["DELETE"])
def reset_personality_test(user_id):
    try:
        if not user_exists(user_id):
            return jsonify({"error": "User not found."}), 404

        if not user_has_personality_test(user_id):
            return jsonify({"error": "This user has no saved personality test."}), 404

        delete_personality_test(user_id)

        return jsonify({
            "message": "Personality test deleted successfully.",
            "has_test": False
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# =========================
# RECOMMENDATION ROUTES
# =========================
@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        if "PASTE_YOUR_NEW_TMDB_TOKEN_HERE" in TMDB_BEARER_TOKEN:
            return jsonify({
                "error": "TMDB token is missing. Paste your TMDB Read Access Token in backend/app.py."
            }), 500

        data = request.get_json(silent=True) or {}

        selected_genre = data.get("genre")
        selected_mood = data.get("mood")
        selected_duration = data.get("duration")
        selected_language = data.get("language")
        content_type = normalize_content_type(data.get("content_type"))
        app_page = parse_app_page(data.get("page"), default=1)

        # For TV we don't require duration since TMDB can't filter by it.
        required_fields_ok = bool(selected_genre and selected_mood and selected_language)
        if content_type == "movie":
            required_fields_ok = required_fields_ok and bool(selected_duration)

        if not required_fields_ok:
            return jsonify({"error": "Missing required fields."}), 400

        if selected_duration and selected_duration not in DURATION_MAP:
            return jsonify({"error": "Invalid duration value."}), 400

        tmdb_pages = get_tmdb_pages_for_app_page(app_page)

        items, max_available_page = discover_items(
            selected_genre=selected_genre,
            selected_language=selected_language,
            selected_duration=selected_duration,
            content_type=content_type,
            tmdb_pages=tmdb_pages
        )

        scored_items = []

        for item in items:
            score, reasons = score_item(
                item=item,
                selected_genre=selected_genre,
                selected_mood=selected_mood,
                selected_duration=selected_duration,
                selected_language=selected_language,
                content_type=content_type
            )
            scored_items.append(format_item(item, score, reasons, content_type))

        sort_scored_items(scored_items)

        top_items = scored_items[:ITEMS_PER_PAGE]
        enrich_match_percentages(top_items)
        enrich_media_details(top_items)

        has_more = max(tmdb_pages) < max_available_page

        return jsonify({
            "page": app_page,
            "content_type": content_type,
            "recommendations": top_items,
            "has_more": has_more
        }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"TMDb request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recommend/personality/<int:user_id>", methods=["GET"])
def recommend_by_personality(user_id):
    try:
        if "PASTE_YOUR_NEW_TMDB_TOKEN_HERE" in TMDB_BEARER_TOKEN:
            return jsonify({
                "error": "TMDB token is missing. Paste your TMDB Read Access Token in backend/app.py."
            }), 500

        if not user_exists(user_id):
            return jsonify({"error": "User not found."}), 404

        row = get_personality_test_row(user_id)

        if row is None:
            return jsonify({"error": "This user has not completed the personality test yet."}), 400

        content_type = normalize_content_type(request.args.get("content_type"))
        app_page = parse_app_page(request.args.get("page"), default=1)

        answers = row_to_answers(row)
        profile = build_personality_profile(answers)
        profile_payload = serialize_profile(profile)

        items, has_more = discover_items_by_personality(profile, content_type, app_page)

        if not items:
            return jsonify({
                "profile": profile_payload,
                "page": app_page,
                "content_type": content_type,
                "recommendations": [],
                "has_more": False
            }), 200

        scored_items = []

        for item in items:
            score, reasons = score_item_by_personality(item, profile, content_type)
            scored_items.append(format_item(item, score, reasons, content_type))

        sort_scored_items(scored_items)

        top_items = scored_items[:ITEMS_PER_PAGE]
        enrich_match_percentages(top_items)
        enrich_media_details(top_items)

        return jsonify({
            "profile": profile_payload,
            "page": app_page,
            "content_type": content_type,
            "recommendations": top_items,
            "has_more": has_more
        }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"TMDb request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
