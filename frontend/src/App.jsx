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

  const handleManualSubmit = async (e) => {
    e.preventDefault();

    setDashboardTab("manual");

    const query = {
      ...formData,
      content_type: contentType
    };

    setLastManualQuery(query);
    await fetchManualRecommendations(query, 1, false);
  };

  const handleManualLoadMore = async () => {
    if (!lastManualQuery || !manualHasMore || manualLoadingMore) return;
    await fetchManualRecommendations(lastManualQuery, manualPage + 1, true);
  };

  const handleLoginChange = (e) => {
    setLoginData({
      ...loginData,
      [e.target.name]: e.target.value
    });
  };

  const handleRegisterChange = (e) => {
    setRegisterData({
      ...registerData,
      [e.target.name]: e.target.value
    });
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);

    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(loginData)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Login failed.");
      }

      persistUser(data.user);
      setDashboardTab("home");
      navigate(data.user.has_personality_test ? "/dashboard" : "/personality-test");
    } catch (err) {
      setAuthError(err.message || "Login failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);

    try {
      const response = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(registerData)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Register failed.");
      }

      setLoginData({
        email: registerData.email,
        password: ""
      });

      setRegisterData({
        username: "",
        email: "",
        password: ""
      });

      navigate("/login");
    } catch (err) {
      setAuthError(err.message || "Register failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("user");
    setUser(null);
    setDashboardTab("home");
    setContentType("movie");
    resetAllRecommendations();
    setPersonalityProfile(null);
    setPersonalityAnswers(createEmptyAnswers());
    navigate("/login");
  };

  const handlePersonalityAnswerChange = (questionId, optionKey) => {
    setPersonalityAnswers((prev) => ({
      ...prev,
      [questionId]: optionKey
    }));
  };

  const handlePersonalitySubmit = async (e) => {
    e.preventDefault();
    if (!user?.id) return;

    setPersonalitySubmitLoading(true);
    setPersonalityError("");
    setPersonalitySuccess("");

    try {
      const response = await fetch(`${API_BASE}/personality-test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_id: user.id,
          answers: personalityAnswers
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not save personality test.");
      }

      setPersonalityProfile(data.profile || null);
      setPersonalitySuccess("Your personality test was saved successfully.");
      updateUser({ has_personality_test: true });
      setDashboardTab("personality");
      navigate("/dashboard");
    } catch (err) {
      setPersonalityError(err.message || "Could not save personality test.");
    } finally {
      setPersonalitySubmitLoading(false);
    }
  };

  const fetchPersonalityRecommendations = async (pageNumber, append) => {
    if (!user?.id) return;

    if (append) {
      setPersonalityLoadingMore(true);
    } else {
      setPersonalityRecommendationsLoading(true);
      setPersonalityRecommendations([]);
    }
    setPersonalityRecommendationsError("");

    try {
      const url = `${API_BASE}/recommend/personality/${user.id}?page=${pageNumber}&content_type=${contentType}`;
      const response = await fetch(url);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not load personality recommendations.");
      }

      if (data.profile) {
        setPersonalityProfile(data.profile);
      }

      const newItems = data.recommendations || [];

      setPersonalityRecommendations((prev) => (append ? [...prev, ...newItems] : newItems));
      setPersonalityPage(pageNumber);
      setPersonalityHasMore(Boolean(data.has_more));
    } catch (err) {
      setPersonalityRecommendationsError(
        err.message || "Could not load personality recommendations."
      );
      if (!append) {
        setPersonalityRecommendations([]);
        setPersonalityHasMore(false);
      }
    } finally {
      setPersonalityRecommendationsLoading(false);
      setPersonalityLoadingMore(false);
    }
  };

  const handleGetPersonalityRecommendations = async () => {
    setDashboardTab("personality");
    await fetchPersonalityRecommendations(1, false);
  };

  const handlePersonalityLoadMore = async () => {
    if (!personalityHasMore || personalityLoadingMore) return;
    await fetchPersonalityRecommendations(personalityPage + 1, true);
  };

  const handleRetakeTest = () => {
    setPersonalitySuccess("");
    setPersonalityError("");
    navigate("/personality-test");
  };

  const answeredCount = Object.values(personalityAnswers).filter(Boolean).length;
  const contentTypeLabel = contentType === "tv" ? "TV series" : "movies";
  const contentTypeSingular = contentType === "tv" ? "TV series" : "movie";

  const actionBtnStyle = (active = false) => ({
    padding: "12px 16px",
    borderRadius: "12px",
    border: active ? "1px solid #111827" : "1px solid #cbd5e1",
    background: active ? "#111827" : "#ffffff",
    color: active ? "#ffffff" : "#111827",
    cursor: "pointer",
    fontWeight: 600,
    boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)"
  });

  const secondaryBtnStyle = {
    padding: "12px 16px",
    borderRadius: "12px",
    border: "1px solid #cbd5e1",
    background: "#f8fafc",
    color: "#111827",
    cursor: "pointer",
    fontWeight: 600,
    boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)"
  };

  const loadMoreBtnStyle = (disabled = false) => ({
    padding: "14px 28px",
    borderRadius: "14px",
    border: "1px solid #111827",
    background: disabled ? "#e5e7eb" : "#111827",
    color: disabled ? "#6b7280" : "#ffffff",
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 600,
    fontSize: "15px",
    boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)"
  });

  const toggleBtnStyle = (active = false) => ({
    padding: "10px 20px",
    borderRadius: "999px",
    border: active ? "1px solid #2563eb" : "1px solid #cbd5e1",
    background: active ? "#2563eb" : "#ffffff",
    color: active ? "#ffffff" : "#111827",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "14px",
    boxShadow: active
      ? "0 4px 12px rgba(37, 99, 235, 0.25)"
      : "0 2px 6px rgba(15, 23, 42, 0.06)"
  });

  const infoCardStyle = {
    background: "#ffffff",
    borderRadius: "16px",
    padding: "16px",
    border: "1px solid #e5e7eb",
    color: "#111827",
    boxShadow: "0 4px 12px rgba(15, 23, 42, 0.06)"
  };

  const pillStyle = {
    padding: "10px 14px",
    borderRadius: "999px",
    background: "#f8fafc",
    border: "1px solid #d1d5db",
    color: "#111827",
    fontWeight: 500
  };

  const watchedBtnStyle = (active = false) => ({
    border: "none",
    borderRadius: "999px",
    padding: "10px 16px",
    fontSize: "0.9rem",
    fontWeight: 700,
    cursor: "pointer",
    background: active ? "#16a34a" : "rgba(255,255,255,0.96)",
    color: active ? "#ffffff" : "#7c4a35",
    boxShadow: "0 8px 18px rgba(0,0,0,0.14)",
    whiteSpace: "nowrap"
  });

  const trailerBtnStyle = (active = false) => ({
    border: "1px solid #f0c7b1",
    borderRadius: "12px",
    padding: "10px 14px",
    fontSize: "0.92rem",
    fontWeight: 700,
    cursor: "pointer",
    background: active ? "#7c4a35" : "#fff7f2",
    color: active ? "#ffffff" : "#7c4a35",
    boxShadow: "0 6px 16px rgba(124,74,53,0.12)"
  });

  const formatRuntimeLabel = (runtimeMinutes) => {
    const totalMinutes = Number(runtimeMinutes || 0);
    if (!totalMinutes) return null;

    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours && minutes) return `${hours}h ${minutes}m`;
    if (hours) return `${hours}h`;
    return `${minutes}m`;
  };

  const formatSeriesInfo = (item) => {
    if (item.content_type !== "tv") return null;

    const parts = [];

    if (item.number_of_seasons) {
      parts.push(
        `${item.number_of_seasons} ${
          item.number_of_seasons === 1 ? "season" : "seasons"
        }`
      );
    }

    if (item.number_of_episodes) {
      parts.push(
        `${item.number_of_episodes} ${
          item.number_of_episodes === 1 ? "episode" : "episodes"
        }`
      );
    }

    return parts.length > 0 ? parts.join(" | ") : null;
  };

  const getMediaLengthLabel = (item) => {
    if ((item.content_type || "movie") === "tv") {
      return formatSeriesInfo(item);
    }

    return formatRuntimeLabel(item.runtime_minutes);
  };

  const toggleTrailer = (movie) => {
    const mediaKey = getMediaCardKey(movie);

    setOpenTrailers((prev) => ({
      ...prev,
      [mediaKey]: !prev[mediaKey]
    }));
  };

  const isTrailerOpen = (movie) => Boolean(openTrailers[getMediaCardKey(movie)]);

  const renderTrailerSection = (movie) => {
    if (!movie.trailer_embed_url) return null;

    const trailerOpen = isTrailerOpen(movie);

    return (
      <div className="movie-trailer-section">
        <button
          type="button"
          onClick={() => toggleTrailer(movie)}
          style={trailerBtnStyle(trailerOpen)}
        >
          {trailerOpen ? "Hide trailer" : "Watch the trailer"}
        </button>

        {trailerOpen && (
          <div className="movie-trailer-frame">
            <iframe
              src={movie.trailer_embed_url}
              title={`Trailer - ${movie.title}`}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          </div>
        )}
      </div>
    );
  };

  const renderWatchedRating = (movie) => {
    const currentRating = Number(movie.user_rating || 5);

    return (
      <div className="movie-rating-card">
        <div className="movie-rating-top">
          <strong>Your rating</strong>
          <span>{currentRating}/10</span>
        </div>

        <input
          type="range"
          min="1"
          max="10"
          step="1"
          value={currentRating}
          onChange={(e) => handleWatchedRatingChange(movie, e.target.value)}
          className="movie-rating-slider"
        />

        <div className="movie-rating-scale">
          <span>1</span>
          <span>10</span>
        </div>
      </div>
    );
  };

  const renderContentTypeToggle = () => (
    <div
      style={{
        display: "flex",
        gap: "10px",
        flexWrap: "wrap",
        alignItems: "center",
        marginTop: "14px"
      }}
    >
      <span style={{ fontWeight: 600, color: "#111827", marginRight: "4px" }}>
        I want to watch:
      </span>
      <button
        type="button"
        onClick={() => handleContentTypeChange("movie")}
        style={toggleBtnStyle(contentType === "movie")}
      >
        🎬 Movies
      </button>
      <button
        type="button"
        onClick={() => handleContentTypeChange("tv")}
        style={toggleBtnStyle(contentType === "tv")}
      >
        📺 TV Series
      </button>
    </div>
  );

  const renderMovieGrid = ({
    items,
    isLoading,
    currentError,
    emptyText,
    onLoadMore,
    hasMoreItems,
    isLoadingMore
  }) => (
    <section className="results-section">
      <div className="section-heading">
        <h2>Recommended {contentTypeLabel}</h2>
        <p>Your best matches appear below.</p>
      </div>

      {currentError && <div className="app-error">{currentError}</div>}

      {isLoading && (
        <div className="loading-card">
          <div className="loader-ring"></div>
          <p>Finding the best {contentTypeLabel} for you...</p>
        </div>
      )}

      {!isLoading && items.length === 0 && !currentError && (
        <div className="empty-card">
          <div className="empty-emoji">{contentType === "tv" ? "📺" : "🎞️"}</div>
          <p>{emptyText}</p>
        </div>
      )}

      <div className="movies-grid">
        {items.map((movie, index) => {
          const watched = isMovieWatched(movie);
          const mediaLengthLabel = getMediaLengthLabel(movie);

          return (
            <div
              key={`${movie.content_type || "movie"}-${movie.id}`}
              className="movie-card"
              style={{ animationDelay: `${(index % 10) * 0.12}s` }}
            >
              <div
                className="movie-poster-wrap"
                style={{
                  position: "relative",
                  overflow: "hidden",
                  borderTopLeftRadius: "inherit",
                  borderTopRightRadius: "inherit"
                }}
              >
                {movie.poster_url ? (
                  <>
                    <img
                      src={movie.poster_url}
                      alt={movie.title}
                      className="movie-poster"
                      style={{
                        filter: watched ? "blur(3px) brightness(0.7)" : "none",
                        transition: "0.3s ease"
                      }}
                    />

                    {watched && (
                      <div
                        style={{
                          position: "absolute",
                          inset: 0,
                          background: "rgba(0,0,0,0.25)"
                        }}
                      />
                    )}

                    {watched && (
                      <div
                        style={{
                          position: "absolute",
                          top: "50%",
                          left: "50%",
                          transform: "translate(-50%, -50%)",
                          color: "#ffffff",
                          fontWeight: 800,
                          fontSize: "18px",
                          background: "rgba(0,0,0,0.6)",
                          padding: "8px 14px",
                          borderRadius: "999px",
                          zIndex: 2,
                          whiteSpace: "nowrap"
                        }}
                      >
                        ✓ WATCHED
                      </div>
                    )}

                    <div className="movie-overlay-actions">
                      <div className="movie-score-badge">
                        {movie.match_percentage
                          ? `${movie.match_percentage}%`
                          : `${movie.score} pts`}
                      </div>

                      <button
                        type="button"
                        onClick={() => toggleWatched(movie)}
                        style={watchedBtnStyle(watched)}
                      >
                        {watched ? "✓ WATCHED" : "WATCH"}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="movie-no-image">No image</div>
                )}
              </div>

              <div className="movie-content">
                <h3>{movie.title}</h3>

                <div className="movie-meta">
                  <span>{movie.release_date || "Unknown date"}</span>
                  <span>
                    ⭐ {movie.vote_average ? movie.vote_average.toFixed(1) : "N/A"}
                  </span>
                  <span>{movie.original_language?.toUpperCase() || "N/A"}</span>
                  {mediaLengthLabel && <span>{mediaLengthLabel}</span>}
                </div>

                <p className="movie-overview">{movie.overview}</p>
                {renderTrailerSection(movie)}

                {movie.why_recommended && movie.why_recommended.length > 0 && (
                  <div className="why-box">
                    <strong>Why recommended</strong>
                    <ul>
                      {movie.why_recommended.map((reason, reasonIndex) => (
                        <li key={reasonIndex}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!isLoading && items.length > 0 && hasMoreItems && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "26px"
          }}
        >
          <button
            type="button"
            onClick={onLoadMore}
            disabled={isLoadingMore}
            style={loadMoreBtnStyle(isLoadingMore)}
          >
            {isLoadingMore ? "Loading more..." : `Load 10 more ${contentTypeLabel}`}
          </button>
        </div>
      )}
    </section>
  );

  const renderProfileCard = () => {
    if (!personalityProfile) {
      return (
        <div className="empty-card">
          <div className="empty-emoji">🧠</div>
          <p>No personality profile yet. Complete the test first.</p>
        </div>
      );
    }

    return (
      <div
        style={{
          display: "grid",
          gap: "16px",
          marginBottom: "28px"
        }}
      >
        <div
          className="glass-panel"
          style={{
            padding: "22px",
            borderRadius: "22px"
          }}
        >
          <div className="section-heading">
            <h2>Your personality profile</h2>
            <p>This profile is generated from your 15-answer personality test.</p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
              marginTop: "10px"
            }}
          >
            <div style={infoCardStyle}>
              <strong>Mood profile</strong>
              <p style={{ marginTop: "8px", color: "#111827" }}>
                {personalityProfile.mood_profile_label || "N/A"}
              </p>
            </div>

            <div style={infoCardStyle}>
              <strong>Discovery level</strong>
              <p style={{ marginTop: "8px", color: "#111827" }}>
                {personalityProfile.discovery_level || "N/A"}
              </p>
            </div>

            <div style={infoCardStyle}>
              <strong>Intensity level</strong>
              <p style={{ marginTop: "8px", color: "#111827" }}>
                {personalityProfile.intensity_level || "N/A"}
              </p>
            </div>

            <div style={infoCardStyle}>
              <strong>Social style</strong>
              <p style={{ marginTop: "8px", color: "#111827" }}>
                {personalityProfile.social_style || "N/A"}
              </p>
            </div>
          </div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: "22px",
            borderRadius: "22px"
          }}
        >
          <div className="section-heading">
            <h2>Top traits</h2>
            <p>The strongest tendencies detected from your answers.</p>
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              marginTop: "10px"
            }}
          >
            {(personalityProfile.top_traits || []).map((trait) => (
              <div key={trait.key} style={pillStyle}>
                {trait.label} ({trait.score})
              </div>
            ))}
          </div>

          <div style={{ marginTop: "20px" }}>
            <strong style={{ color: "#111827" }}>Recommended genres</strong>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "10px",
                marginTop: "10px"
              }}
            >
              {(personalityProfile.recommended_genres || []).map((genre) => (
                <div key={genre} style={pillStyle}>
                  {genre}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (route === "/register") {
    return (
      <div className="auth-page">
        <div className="bg-shape shape-1"></div>
        <div className="bg-shape shape-2"></div>
        <div className="bg-shape shape-3"></div>

        <div className="auth-card auth-card-register">
          <div className="auth-badge">Create your account</div>
          <h2>Join the movie journey</h2>
          <p className="auth-subtitle">
            Build your profile and start receiving warm, personalized recommendations.
          </p>

          <form onSubmit={handleRegisterSubmit} className="auth-form">
            <input
              type="text"
              name="username"
              placeholder="Username"
              value={registerData.username}
              onChange={handleRegisterChange}
              required
            />

            <input
              type="email"
              name="email"
              placeholder="Email"
              value={registerData.email}
              onChange={handleRegisterChange}
              required
            />

            <input
              type="password"
              name="password"
              placeholder="Password"
              value={registerData.password}
              onChange={handleRegisterChange}
              required
            />

            {authError && <div className="auth-error">{authError}</div>}

            <button type="submit" className="auth-btn">
              {authLoading ? "Registering..." : "Create account"}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account?{" "}
            <span onClick={() => navigate("/login")}>Login</span>
          </p>
        </div>
      </div>
    );
  }

  if (route === "/login") {
    return (
      <div className="auth-page">
        <div className="bg-shape shape-1"></div>
        <div className="bg-shape shape-2"></div>
        <div className="bg-shape shape-3"></div>

        <div className="auth-card">
          <div className="auth-badge">Welcome back</div>
          <h2>Login to continue</h2>
          <p className="auth-subtitle">
            Find films that match your personality, mood and cinematic vibe.
          </p>

          <form onSubmit={handleLoginSubmit} className="auth-form">
            <input
              type="email"
              name="email"
              placeholder="Email"
              value={loginData.email}
              onChange={handleLoginChange}
              required
            />

            <input
              type="password"
              name="password"
              placeholder="Password"
              value={loginData.password}
              onChange={handleLoginChange}
              required
            />

            {authError && <div className="auth-error">{authError}</div>}

            <button type="submit" className="auth-btn">
              {authLoading ? "Logging in..." : "Login"}
            </button>
          </form>

          <p className="auth-switch">
            Don’t have an account?{" "}
            <span onClick={() => navigate("/register")}>Register</span>
          </p>
        </div>
      </div>
    );
  }

  if (route === "/personality-test") {
    return (
      <div className="app-page">
        <div className="bg-shape shape-1"></div>
        <div className="bg-shape shape-2"></div>
        <div className="bg-shape shape-3"></div>

        <div className="app-container">
          <div className="topbar">
            <div>
              <div className="topbar-badge">Personality onboarding</div>
              <h1>15-question personality test</h1>
              <p>
                Complete this test once, save it to your account, and use it anytime for
                automatic recommendations.
              </p>
            </div>

            <div className="topbar-right">
              <div className="welcome-box">
                Welcome, <strong>{user?.username || "User"}</strong>
              </div>

              {user?.has_personality_test && (
                <button onClick={() => navigate("/dashboard")} className="logout-btn">
                  Back to dashboard
                </button>
              )}
            </div>
          </div>

          <div
            className="glass-panel"
            style={{
              padding: "24px",
              borderRadius: "22px",
              marginBottom: "26px"
            }}
          >
            <div className="section-heading">
              <h2>Your progress</h2>
              <p>{answeredCount} / 15 answers completed.</p>
            </div>

            <div
              style={{
                width: "100%",
                height: "10px",
                background: "#e5e7eb",
                borderRadius: "999px",
                overflow: "hidden",
                marginTop: "12px"
              }}
            >
              <div
                style={{
                  width: `${(answeredCount / 15) * 100}%`,
                  height: "100%",
                  background: "linear-gradient(90deg, #2563eb, #7c3aed)"
                }}
              ></div>
            </div>

            {personalitySuccess && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "12px",
                  borderRadius: "12px",
                  background: "#dcfce7",
                  color: "#166534",
                  border: "1px solid #86efac"
                }}
              >
                {personalitySuccess}
              </div>
            )}

            {personalityError && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "12px",
                  borderRadius: "12px",
                  background: "#fee2e2",
                  color: "#991b1b",
                  border: "1px solid #fca5a5"
                }}
              >
                {personalityError}
              </div>
            )}
          </div>

          <form onSubmit={handlePersonalitySubmit}>
            {personalityLoading ? (
              <div className="loading-card">
                <div className="loader-ring"></div>
                <p>Loading your personality test...</p>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gap: "18px"
                }}
              >
                {personalityQuestions.map((item, index) => (
                  <div
                    key={item.id}
                    className="glass-panel"
                    style={{
                      padding: "22px",
                      borderRadius: "22px"
                    }}
                  >
                    <div className="section-heading">
                      <h2 style={{ fontSize: "20px", marginBottom: "6px", color: "#111827" }}>
                        {index + 1}. {item.question}
                      </h2>
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gap: "10px",
                        marginTop: "12px"
                      }}
                    >
                      {Object.entries(item.options).map(([key, label]) => {
                        const isSelected = personalityAnswers[item.id] === key;

                        return (
                          <button
                            key={key}
                            type="button"
                            onClick={() => handlePersonalityAnswerChange(item.id, key)}
                            style={{
                              padding: "14px 16px",
                              borderRadius: "14px",
                              border: isSelected
                                ? "1px solid #2563eb"
                                : "1px solid #cbd5e1",
                              background: isSelected ? "#dbeafe" : "#ffffff",
                              color: "#111827",
                              textAlign: "left",
                              cursor: "pointer",
                              fontSize: "15px",
                              fontWeight: isSelected ? 600 : 500,
                              boxShadow: "0 4px 12px rgba(15, 23, 42, 0.06)"
                            }}
                          >
                            <strong style={{ marginRight: "8px", color: "#1d4ed8" }}>
                              {key}.
                            </strong>
                            <span style={{ color: "#111827" }}>{label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}

                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    flexWrap: "wrap",
                    justifyContent: "flex-end",
                    marginTop: "6px"
                  }}
                >
                  {user?.has_personality_test && (
                    <button
                      type="button"
                      onClick={() => navigate("/dashboard")}
                      style={secondaryBtnStyle}
                    >
                      Cancel
                    </button>
                  )}

                  <button
                    type="submit"
                    className="recommend-btn"
                    style={{
                      background: "#111827",
                      color: "#ffffff",
                      border: "none"
                    }}
                  >
                    {personalitySubmitLoading
                      ? "Saving test..."
                      : user?.has_personality_test
                      ? "Update personality test"
                      : "Save personality test"}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>
    );
  }

  if (route === "/watched") {
    const watchedList = getUserWatchedItems();
    const watchedMovies = watchedList.filter((item) => (item.content_type || "movie") === "movie");
    const watchedSeries = watchedList.filter((item) => item.content_type === "tv");

    return (
      <div className="app-page">
        <div className="bg-shape shape-1"></div>
        <div className="bg-shape shape-2"></div>
        <div className="bg-shape shape-3"></div>

        <div className="app-container">
          <div className="topbar">
            <div>
              <div className="topbar-badge">Your watched library</div>
              <h1>Watched movies & series</h1>
              <p>Here you can find everything you marked as watched.</p>
            </div>

            <div className="topbar-right">
              <div className="welcome-box">
                Welcome, <strong>{user?.username || "User"}</strong>
              </div>
              <button onClick={() => navigate("/dashboard")} className="logout-btn">
                Back to dashboard
              </button>
            </div>
          </div>

          <div
            className="glass-panel"
            style={{
              padding: "22px",
              borderRadius: "22px",
              marginBottom: "26px"
            }}
          >
            <div className="section-heading">
              <h2>Your watched collection</h2>
              <p>
                Total watched items: <strong>{watchedList.length}</strong>
              </p>
            </div>

            <div
              style={{
                display: "flex",
                gap: "12px",
                flexWrap: "wrap",
                marginTop: "14px"
              }}
            >
              <div style={pillStyle}>🎬 Movies: {watchedMovies.length}</div>
              <div style={pillStyle}>📺 TV Series: {watchedSeries.length}</div>
            </div>
          </div>

          <section className="results-section">
            <div className="section-heading">
              <h2>All watched items</h2>
              <p>You can remove any item by pressing the watched button again.</p>
            </div>

            {watchedList.length === 0 && (
              <div className="empty-card">
                <div className="empty-emoji">🍿</div>
                <p>You have not marked any movies or TV series as watched yet.</p>
              </div>
            )}

            <div className="movies-grid">
              {watchedList.map((movie, index) => {
                const watched = isMovieWatched(movie);
                const mediaLengthLabel = getMediaLengthLabel(movie);

                return (
                  <div
                    key={`${movie.content_type || "movie"}-${movie.id}`}
                    className="movie-card"
                    style={{ animationDelay: `${(index % 10) * 0.12}s` }}
                  >
                    <div
                      className="movie-poster-wrap"
                      style={{
                        position: "relative",
                        overflow: "hidden",
                        borderTopLeftRadius: "inherit",
                        borderTopRightRadius: "inherit"
                      }}
                    >
                      {movie.poster_url ? (
                        <>
                          <img
                            src={movie.poster_url}
                            alt={movie.title}
                            className="movie-poster"
                            style={{
                              filter: watched ? "blur(3px) brightness(0.7)" : "none",
                              transition: "0.3s ease"
                            }}
                          />

                          {watched && (
                            <div
                              style={{
                                position: "absolute",
                                inset: 0,
                                background: "rgba(0,0,0,0.25)"
                              }}
                            />
                          )}

                          {watched && (
                            <div
                              style={{
                                position: "absolute",
                                top: "50%",
                                left: "50%",
                                transform: "translate(-50%, -50%)",
                                color: "#ffffff",
                                fontWeight: 800,
                                fontSize: "18px",
                                background: "rgba(0,0,0,0.6)",
                                padding: "8px 14px",
                                borderRadius: "999px",
                                zIndex: 2,
                                whiteSpace: "nowrap"
                              }}
                            >
                              ✓ WATCHED
                            </div>
                          )}

                          <div className="movie-overlay-actions">
                            <div className="movie-score-badge">
                              {movie.content_type === "tv" ? "TV Series" : "Movie"}
                            </div>

                            <button
                              type="button"
                              onClick={() => toggleWatched(movie)}
                              style={watchedBtnStyle(watched)}
                            >
                              {watched ? "✓ WATCHED" : "WATCH"}
                            </button>
                          </div>
                        </>
                      ) : (
                        <div className="movie-no-image">No image</div>
                      )}
                    </div>

                    <div className="movie-content">
                      <h3>{movie.title}</h3>

                      <div className="movie-meta">
                        <span>{movie.release_date || "Unknown date"}</span>
                        <span>
                          ⭐ {movie.vote_average ? movie.vote_average.toFixed(1) : "N/A"}
                        </span>
                        <span>{movie.original_language?.toUpperCase() || "N/A"}</span>
                        {mediaLengthLabel && <span>{mediaLengthLabel}</span>}
                      </div>

                      <p className="movie-overview">{movie.overview}</p>
                      {renderWatchedRating(movie)}
                      {renderTrailerSection(movie)}

                      {movie.saved_at && (
                        <div
                          style={{
                            marginTop: "14px",
                            fontSize: "0.9rem",
                            color: "#64748b",
                            fontWeight: 600
                          }}
                        >
                          Saved as watched: {new Date(movie.saved_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="app-page">
      <div className="bg-shape shape-1"></div>
      <div className="bg-shape shape-2"></div>
      <div className="bg-shape shape-3"></div>

      <div className="app-container">
        <div className="topbar">
          <div>
            <div className="topbar-badge">Personalized picks</div>
            <h1>Movie & Series Recommendation System</h1>
            <p>
              Choose between manual recommendations and automatic picks based on your
              personality profile.
            </p>
          </div>

          <div className="topbar-right">
            <div className="welcome-box">
              Welcome, <strong>{user?.username || "User"}</strong>
            </div>
            <button onClick={handleLogout} className="logout-btn">
              Logout
            </button>
          </div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: "22px",
            borderRadius: "22px",
            marginBottom: "26px"
          }}
        >
          <div className="section-heading">
            <h2>Choose your recommendation mode</h2>
            <p>
              You can use your saved personality profile or manually select today's
              viewing preferences.
            </p>
          </div>

          {renderContentTypeToggle()}

          <div
            style={{
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
              marginTop: "14px"
            }}
          >
            <button
              type="button"
              onClick={() => {
                setDashboardTab("personality");
                handleGetPersonalityRecommendations();
              }}
              style={actionBtnStyle(dashboardTab === "personality")}
            >
              Recommend by personality
            </button>

            <button
              type="button"
              onClick={() => setDashboardTab("manual")}
              style={actionBtnStyle(dashboardTab === "manual")}
            >
              Recommend manually
            </button>

            <button
              type="button"
              onClick={() => navigate("/watched")}
              style={secondaryBtnStyle}
            >
              Watched list
            </button>

            <button
              type="button"
              onClick={handleRetakeTest}
              style={secondaryBtnStyle}
            >
              Retake personality test
            </button>
          </div>
        </div>

        {dashboardTab === "home" && (
          <div className="main-grid">
            <section className="glass-panel form-panel">
              <div className="section-heading">
                <h2>Your saved profile</h2>
                <p>Quick overview of the cinematic personality you built.</p>
              </div>
              {renderProfileCard()}
            </section>

            <section className="glass-panel info-panel">
              <div className="section-heading">
                <h2>How it works</h2>
                <p>A dual recommendation flow built around your style.</p>
              </div>

              <div className="info-list">
                <div className="info-item">
                  <span>01</span>
                  <div>
                    <h4>Personality mode</h4>
                    <p>Uses your saved 15-question test to recommend movies or TV series automatically.</p>
                  </div>
                </div>

                <div className="info-item">
                  <span>02</span>
                  <div>
                    <h4>Manual mode</h4>
                    <p>Lets you choose genre, mood, duration and language yourself.</p>
                  </div>
                </div>

                <div className="info-item">
                  <span>03</span>
                  <div>
                    <h4>Movies or series</h4>
                    <p>Switch between movies and TV series at any time with a single click.</p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {dashboardTab === "manual" && (
          <>
            <div className="main-grid">
              <section className="glass-panel form-panel">
                <div className="section-heading">
                  <h2>Manual recommendations</h2>
                  <p>Tell us what you feel like watching today.</p>
                </div>

                <form onSubmit={handleManualSubmit} className="recommend-form">
                  <div className="form-group">
                    <label>Genre</label>
                    <select
                      name="genre"
                      value={formData.genre}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Choose genre</option>
                      <option value="Sci-Fi">Sci-Fi</option>
                      <option value="Action">Action</option>
                      <option value="Romance">Romance</option>
                      <option value="Comedy">Comedy</option>
                      <option value="Drama">Drama</option>
                      <option value="Mystery">Mystery</option>
                      <option value="Crime">Crime</option>
                      <option value="Animation">Animation</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Mood</label>
                    <select
                      name="mood"
                      value={formData.mood}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Choose mood</option>
                      <option value="Intense">Intense</option>
                      <option value="Dark">Dark</option>
                      <option value="Emotional">Emotional</option>
                      <option value="Fun">Fun</option>
                    </select>
                  </div>

                  {contentType === "movie" && (
                    <div className="form-group">
                      <label>Duration</label>
                      <select
                        name="duration"
                        value={formData.duration}
                        onChange={handleChange}
                        required
                      >
                        <option value="">Choose duration</option>
                        <option value="Short">Short</option>
                        <option value="Medium">Medium</option>
                        <option value="Long">Long</option>
                      </select>
                    </div>
                  )}

                  <div className="form-group">
                    <label>Language</label>
                    <select
                      name="language"
                      value={formData.language}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Choose language</option>
                      <option value="English">English</option>
                      <option value="French">French</option>
                      <option value="Spanish">Spanish</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    className="recommend-btn"
                    disabled={manualLoading}
                    style={{
                      background: "#111827",
                      color: "#ffffff",
                      border: "none"
                    }}
                  >
                    {manualLoading
                      ? "Searching..."
                      : `Get manual ${contentTypeLabel}`}
                  </button>
                </form>
              </section>

              <section className="glass-panel info-panel">
                <div className="section-heading">
                  <h2>Manual mode</h2>
                  <p>
                    This mode is useful when you want recommendations for a specific
                    moment.
                  </p>
                </div>

                <div className="info-list">
                  <div className="info-item">
                    <span>01</span>
                    <div>
                      <h4>Pick your current vibe</h4>
                      <p>Use mood and genre to guide the search more directly.</p>
                    </div>
                  </div>

                  <div className="info-item">
                    <span>02</span>
                    <div>
                      <h4>Control the experience</h4>
                      <p>
                        Choose the runtime and original language you want right now.
                      </p>
                    </div>
                  </div>

                  <div className="info-item">
                    <span>03</span>
                    <div>
                      <h4>Instant list</h4>
                      <p>
                        Get {contentTypeLabel} ranked by the compatibility score from
                        the backend.
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {renderMovieGrid({
              items: manualRecommendations,
              isLoading: manualLoading,
              currentError: manualError,
              emptyText: `No manual ${contentTypeLabel} yet. Choose your preferences to begin.`,
              onLoadMore: handleManualLoadMore,
              hasMoreItems: manualHasMore,
              isLoadingMore: manualLoadingMore
            })}
          </>
        )}

        {dashboardTab === "personality" && (
          <>
            {renderProfileCard()}

            <div
              className="glass-panel"
              style={{
                padding: "22px",
                borderRadius: "22px",
                marginBottom: "26px"
              }}
            >
              <div className="section-heading">
                <h2>Personality-based recommendations</h2>
                <p>
                  Use your saved profile to automatically discover {contentTypeLabel}{" "}
                  that fit your personality.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  flexWrap: "wrap",
                  marginTop: "14px"
                }}
              >
                <button
                  type="button"
                  onClick={handleGetPersonalityRecommendations}
                  disabled={personalityRecommendationsLoading}
                  className="recommend-btn"
                  style={{
                    width: "auto",
                    background: "#111827",
                    color: "#ffffff",
                    border: "none"
                  }}
                >
                  {personalityRecommendationsLoading
                    ? "Loading recommendations..."
                    : `Get ${contentTypeSingular} recommendations for my personality`}
                </button>
              </div>
            </div>

            {renderMovieGrid({
              items: personalityRecommendations,
              isLoading: personalityRecommendationsLoading,
              currentError: personalityRecommendationsError,
              emptyText: `No personality-based ${contentTypeLabel} yet. Click the button above.`,
              onLoadMore: handlePersonalityLoadMore,
              hasMoreItems: personalityHasMore,
              isLoadingMore: personalityLoadingMore
            })}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
