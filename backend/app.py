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
