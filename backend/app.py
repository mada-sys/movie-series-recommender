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
