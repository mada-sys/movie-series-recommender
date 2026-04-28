
import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:5000";

function createEmptyAnswers() {
  const answers = {};
  for (let i = 1; i <= 15; i += 1) {
    answers[`q${i}`] = "";
  }
  return answers;
}

function App() {
  const [route, setRoute] = useState(window.location.pathname);

  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem("user");
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [watchedItems, setWatchedItems] = useState(() => {
    const savedWatched = localStorage.getItem("watchedItems");
    return savedWatched ? JSON.parse(savedWatched) : {};
  });
  const [openTrailers, setOpenTrailers] = useState({});

  const [dashboardTab, setDashboardTab] = useState("home");
  const [contentType, setContentType] = useState("movie");

  const [formData, setFormData] = useState({
    genre: "",
    mood: "",
    duration: "",
    language: ""
  });

  const [manualRecommendations, setManualRecommendations] = useState([]);
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState("");
  const [manualPage, setManualPage] = useState(1);
  const [manualHasMore, setManualHasMore] = useState(false);
  const [manualLoadingMore, setManualLoadingMore] = useState(false);
  const [lastManualQuery, setLastManualQuery] = useState(null);

  const [loginData, setLoginData] = useState({
    email: "",
    password: ""
  });

  const [registerData, setRegisterData] = useState({
    username: "",
    email: "",
    password: ""
  });

  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const [personalityQuestions, setPersonalityQuestions] = useState([]);
  const [personalityAnswers, setPersonalityAnswers] = useState(createEmptyAnswers());
  const [personalityProfile, setPersonalityProfile] = useState(null);
  const [personalityError, setPersonalityError] = useState("");
  const [personalitySuccess, setPersonalitySuccess] = useState("");
  const [personalityLoading, setPersonalityLoading] = useState(false);
  const [personalitySubmitLoading, setPersonalitySubmitLoading] = useState(false);

  const [personalityRecommendations, setPersonalityRecommendations] = useState([]);
  const [personalityRecommendationsLoading, setPersonalityRecommendationsLoading] = useState(false);
  const [personalityRecommendationsError, setPersonalityRecommendationsError] = useState("");
  const [personalityPage, setPersonalityPage] = useState(1);
  const [personalityHasMore, setPersonalityHasMore] = useState(false);
  const [personalityLoadingMore, setPersonalityLoadingMore] = useState(false);

  const navigate = (path) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    setRoute(path);
  };

  const persistUser = (nextUser) => {
    if (nextUser) {
      localStorage.setItem("user", JSON.stringify(nextUser));
    } else {
      localStorage.removeItem("user");
    }
    setUser(nextUser);
  };

  const updateUser = (updates) => {
    if (!user) return;
    const nextUser = { ...user, ...updates };
    persistUser(nextUser);
  };

  const getWatchedKey = (movie) => {
    const userId = user?.id || "guest";
    const type = movie.content_type || contentType || "movie";
    return `${userId}-${type}-${movie.id}`;
  };

  const getMediaCardKey = (movie) => {
    const type = movie.content_type || contentType || "movie";
    return `${type}-${movie.id}`;
  };

  const isMovieWatched = (movie) => {
    return Boolean(watchedItems[getWatchedKey(movie)]);
  };

  const updateWatchedItem = (movie, updates) => {
    const key = getWatchedKey(movie);

    setWatchedItems((prev) => {
      if (!prev[key]) return prev;

      const next = {
        ...prev,
        [key]: {
          ...prev[key],
          ...updates
        }
      };

      localStorage.setItem("watchedItems", JSON.stringify(next));
      return next;
    });
  };
