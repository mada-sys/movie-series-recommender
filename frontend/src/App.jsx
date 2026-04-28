
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

const toggleWatched = (movie) => {
    const key = getWatchedKey(movie);

    setWatchedItems((prev) => {
      const next = { ...prev };

      if (next[key]) {
        delete next[key];
      } else {
        next[key] = {
          ...movie,
          content_type: movie.content_type || contentType || "movie",
          user_rating: Number(movie.user_rating || 5),
          media_details_loaded: Boolean(movie.media_details_loaded),
          saved_at: new Date().toISOString()
        };
      }

      localStorage.setItem("watchedItems", JSON.stringify(next));
      return next;
    });
  };

  const getUserWatchedItems = () => {
    const userId = user?.id || "guest";

    return Object.entries(watchedItems)
      .filter(([key]) => key.startsWith(`${userId}-`))
      .map(([, value]) => value)
      .sort((a, b) => new Date(b.saved_at || 0) - new Date(a.saved_at || 0));
  };

  const handleWatchedRatingChange = (movie, nextRating) => {
    updateWatchedItem(movie, { user_rating: Number(nextRating) });
  };

  const needsMediaDetails = (item) => !item.media_details_loaded;

  const resetAllRecommendations = () => {
    setManualRecommendations([]);
    setManualPage(1);
    setManualHasMore(false);
    setManualError("");
    setLastManualQuery(null);

    setPersonalityRecommendations([]);
    setPersonalityPage(1);
    setPersonalityHasMore(false);
    setPersonalityRecommendationsError("");
  };

  useEffect(() => {
    const handlePopState = () => {
      setRoute(window.location.pathname);
    };

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useEffect(() => {
    setAuthError("");
  }, [route]);

  useEffect(() => {
    const authRoutes = ["/login", "/register"];

    if (!user) {
      if (!authRoutes.includes(route)) {
        navigate("/login");
      }
      return;
    }

    if (route === "/" || authRoutes.includes(route)) {
      navigate(user.has_personality_test ? "/dashboard" : "/personality-test");
      return;
    }

    if (route === "/dashboard" && !user.has_personality_test) {
      navigate("/personality-test");
    }
  }, [user, route]);

  useEffect(() => {
    if (!user?.id) return;

    const syncStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/personality-test/status/${user.id}`);
        const data = await response.json();

        if (!response.ok) return;

        if (data.has_test !== user.has_personality_test) {
          updateUser({ has_personality_test: data.has_test });
        }
      } catch (err) {
        console.error("Could not sync personality test status.", err);
      }
    };

    syncStatus();
  }, [user?.id]);

useEffect(() => {
    if (!user?.id) return;

    if (route === "/personality-test") {
      fetchPersonalityQuestions();
      fetchPersonalityData(user.id);
    }

    if (route === "/dashboard" && user.has_personality_test) {
      fetchPersonalityData(user.id);
    }
  }, [route, user?.id, user?.has_personality_test]);

  useEffect(() => {
    if (route !== "/watched") return;

    const userId = user?.id || "guest";
    const watchedEntries = Object.entries(watchedItems).filter(
      ([key, item]) => key.startsWith(`${userId}-`) && item?.id && needsMediaDetails(item)
    );

    if (watchedEntries.length === 0) return;

    let cancelled = false;

    const syncWatchedMediaDetails = async () => {
      try {
        const results = await Promise.all(
          watchedEntries.map(async ([key, item]) => {
            const type = item.content_type || "movie";
            const response = await fetch(`${API_BASE}/media-details/${type}/${item.id}`);
            const data = await response.json();

            if (!response.ok) {
              throw new Error(data.error || "Could not load media details.");
            }

            return { key, data };
          })
        );

        if (cancelled) return;

        setWatchedItems((prev) => {
          const next = { ...prev };
          let changed = false;

          results.forEach(({ key, data }) => {
            if (!next[key]) return;

            next[key] = {
              ...next[key],
              ...data,
              media_details_loaded: true
            };
            changed = true;
          });

          if (!changed) return prev;

          localStorage.setItem("watchedItems", JSON.stringify(next));
          return next;
        });
      } catch (err) {
        console.error("Could not sync watched media details.", err);
      }
    };

    syncWatchedMediaDetails();

    return () => {
      cancelled = true;
    };
  }, [route, user?.id, watchedItems]);

  const fetchPersonalityQuestions = async () => {
    if (personalityQuestions.length > 0) return;

    try {
      const response = await fetch(`${API_BASE}/personality-questions`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not load personality questions.");
      }

      setPersonalityQuestions(data);
    } catch (err) {
      setPersonalityError(err.message || "Could not load personality questions.");
    }
  };

  const fetchPersonalityData = async (userId) => {
    setPersonalityLoading(true);
    setPersonalityError("");

    try {
      const response = await fetch(`${API_BASE}/personality-test/${userId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not load personality test.");
      }

      if (data.has_test) {
        setPersonalityAnswers(data.answers || createEmptyAnswers());
        setPersonalityProfile(data.profile || null);
        updateUser({ has_personality_test: true });
      } else {
        setPersonalityAnswers(createEmptyAnswers());
        setPersonalityProfile(null);
        setPersonalityRecommendations([]);
        setPersonalityPage(1);
        setPersonalityHasMore(false);
        updateUser({ has_personality_test: false });
      }
    } catch (err) {
      setPersonalityError(err.message || "Could not load personality test.");
    } finally {
      setPersonalityLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleContentTypeChange = (newType) => {
    if (newType === contentType) return;
    setContentType(newType);
    resetAllRecommendations();
  };

  const fetchManualRecommendations = async (query, pageNumber, append) => {
    if (!query) return;

    if (append) {
      setManualLoadingMore(true);
    } else {
      setManualLoading(true);
      setManualRecommendations([]);
    }
    setManualError("");

    try {
      const response = await fetch(`${API_BASE}/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          ...query,
          page: pageNumber
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
      }

      const newItems = data.recommendations || [];

      setManualRecommendations((prev) => (append ? [...prev, ...newItems] : newItems));
      setManualPage(pageNumber);
      setManualHasMore(Boolean(data.has_more));
    } catch (err) {
      setManualError(err.message || "Request failed.");
      if (!append) {
        setManualRecommendations([]);
        setManualHasMore(false);
      }
    } finally {
      setManualLoading(false);
      setManualLoadingMore(false);
    }
  };
