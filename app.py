from __future__ import annotations

import os
import re
from difflib import get_close_matches
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
import requests
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_DATASET = "data/movies_clean.csv"
FALLBACK_DATASET = "data/sample_movies.csv"
REQUIRED_COLUMNS = ["title", "genres", "overview", "cast", "director", "keywords", "vote_average"]
GENRES = ["Action", "Comedy", "Sci-Fi", "Romance", "Thriller", "Drama", "Adventure", "Crime", "Mystery"]
LANGUAGE_OPTIONS = ["Any", "English", "Hindi", "Telugu", "Kannada", "Tamil", "Malayalam"]
INDUSTRY_OPTIONS = ["Any", "Hollywood", "Bollywood", "Tollywood", "Sandalwood", "Kollywood", "Mollywood"]
WEIGHTS = {
    "favorite": 0.4,
    "history": 0.3,
    "genre": 0.3,
}


@dataclass(frozen=True)
class RecommendationReason:
    favorite_match: str | None
    history_match: str | None
    genre_match: bool
    shared_director: str | None
    shared_cast: str | None


def normalize_title(title: str) -> str:
    title = re.sub(r"\(\d{4}\)", "", str(title))
    return " ".join(title.lower().strip().split())


def split_user_movies(raw_text: str) -> list[str]:
    values = []
    for line in raw_text.replace(";", "\n").splitlines():
        for item in line.split(","):
            cleaned = item.strip()
            if cleaned:
                values.append(cleaned)
    return values


def safe_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def load_dataset(uploaded_file) -> pd.DataFrame:
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
    else:
        dataset_path = DEFAULT_DATASET if os.path.exists(DEFAULT_DATASET) else FALLBACK_DATASET
        data = pd.read_csv(dataset_path)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        joined = ", ".join(missing_columns)
        st.error(f"Dataset is missing required columns: {joined}")
        st.stop()

    for column in REQUIRED_COLUMNS:
        data[column] = data[column].apply(safe_text)

    if "poster_path" not in data.columns:
        data["poster_path"] = ""
    else:
        data["poster_path"] = data["poster_path"].apply(safe_text)
    if "language" not in data.columns:
        data["language"] = "Unknown"
    else:
        data["language"] = data["language"].apply(safe_text).replace("", "Unknown")
    if "industry" not in data.columns:
        data["industry"] = "Unknown"
    else:
        data["industry"] = data["industry"].apply(safe_text).replace("", "Unknown")

    data["vote_average"] = pd.to_numeric(data["vote_average"], errors="coerce").fillna(0)
    data["normalized_title"] = data["title"].apply(normalize_title)
    data = data.drop_duplicates(subset=["normalized_title"]).reset_index(drop=True)
    data["tags"] = (
        data["genres"]
        + " "
        + data["cast"]
        + " "
        + data["director"]
        + " "
        + data["keywords"]
        + " "
        + data["overview"]
    ).str.lower()
    return data


@st.cache_data(show_spinner=False)
def build_similarity(data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    vectorizer = TfidfVectorizer(stop_words="english", max_features=7000)
    vectors = vectorizer.fit_transform(data["tags"])
    similarity = cosine_similarity(vectors)
    return vectors, similarity


def find_movie_indices(data: pd.DataFrame, titles: Iterable[str]) -> list[int]:
    title_to_index = {title: index for index, title in enumerate(data["normalized_title"])}
    normalized_titles = list(title_to_index.keys())
    indices = []
    for title in titles:
        normalized = normalize_title(title)
        if normalized in title_to_index:
            indices.append(title_to_index[normalized])
            continue
        if len(normalized) >= 4:
            partial_matches = data.index[
                data["normalized_title"].str.startswith(normalized)
                | data["normalized_title"].str.contains(normalized, regex=False)
            ].tolist()
            if partial_matches:
                indices.append(partial_matches[0])
                continue
            close_matches = get_close_matches(normalized, normalized_titles, n=1, cutoff=0.78)
            if close_matches:
                indices.append(title_to_index[close_matches[0]])
    return indices


def average_similarity(similarity: np.ndarray, indices: list[int], movie_count: int) -> np.ndarray:
    if not indices:
        return np.zeros(movie_count)
    return similarity[indices].mean(axis=0)


def genre_score(data: pd.DataFrame, selected_genre: str) -> np.ndarray:
    selected = selected_genre.lower()
    return data["genres"].str.lower().str.contains(selected, regex=False).astype(float).to_numpy()


def best_source_movie(data: pd.DataFrame, similarity: np.ndarray, source_indices: list[int], target_index: int) -> str | None:
    if not source_indices:
        return None
    best_index = max(source_indices, key=lambda source_index: similarity[source_index][target_index])
    if similarity[best_index][target_index] <= 0:
        return None
    return data.loc[best_index, "title"]


def shared_value(source_values: Iterable[str], target_text: str) -> str | None:
    target_lower = target_text.lower()
    for value in source_values:
        cleaned = value.strip()
        if cleaned and cleaned.lower() in target_lower:
            return cleaned
    return None


def build_reason(
    data: pd.DataFrame,
    similarity: np.ndarray,
    favorite_indices: list[int],
    history_indices: list[int],
    selected_genre: str,
    target_index: int,
) -> RecommendationReason:
    source_indices = favorite_indices + history_indices
    source_directors = [data.loc[index, "director"] for index in source_indices]
    source_cast = " ".join(data.loc[index, "cast"] for index in source_indices).split()

    return RecommendationReason(
        favorite_match=best_source_movie(data, similarity, favorite_indices, target_index),
        history_match=best_source_movie(data, similarity, history_indices, target_index),
        genre_match=selected_genre.lower() in data.loc[target_index, "genres"].lower(),
        shared_director=shared_value(source_directors, data.loc[target_index, "director"]),
        shared_cast=shared_value(source_cast, data.loc[target_index, "cast"]),
    )


def tmdb_poster_url(poster_path: str, api_key: str) -> str | None:
    if not poster_path or poster_path.lower() == "nan":
        return None
    if poster_path.startswith("http"):
        return poster_path
    if not api_key:
        return None
    return f"https://image.tmdb.org/t/p/w342/{poster_path.lstrip('/')}"


def tmdb_search_poster(title: str, api_key: str) -> str | None:
    if not api_key:
        return None
    try:
        response = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": api_key, "query": title},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except requests.RequestException:
        return None
    if not results or not results[0].get("poster_path"):
        return None
    return f"https://image.tmdb.org/t/p/w342/{results[0]['poster_path'].lstrip('/')}"


def recommend(
    data: pd.DataFrame,
    similarity: np.ndarray,
    favorite_movies: list[str],
    watched_movies: list[str],
    selected_genre: str,
    selected_language: str,
    selected_industry: str,
    top_n: int = 10,
) -> pd.DataFrame:
    movie_count = len(data)
    favorite_indices = find_movie_indices(data, favorite_movies)
    history_indices = find_movie_indices(data, watched_movies)

    favorite_scores = average_similarity(similarity, favorite_indices, movie_count)
    history_scores = average_similarity(similarity, history_indices, movie_count)
    genre_scores = genre_score(data, selected_genre)
    rating_scores = (data["vote_average"].to_numpy() / 10).clip(0, 1)

    if favorite_indices or history_indices:
        final_scores = (
            WEIGHTS["favorite"] * favorite_scores
            + WEIGHTS["history"] * history_scores
            + WEIGHTS["genre"] * genre_scores
        )
    else:
        final_scores = (0.7 * genre_scores) + (0.3 * rating_scores)

    excluded = set(favorite_indices + history_indices)
    candidates = []
    for index, score in enumerate(final_scores):
        if index in excluded:
            continue
        if selected_language != "Any" and data.loc[index, "language"].lower() != selected_language.lower():
            continue
        if selected_industry != "Any" and data.loc[index, "industry"].lower() != selected_industry.lower():
            continue
        reason = build_reason(data, similarity, favorite_indices, history_indices, selected_genre, index)
        candidates.append(
            {
                "index": index,
                "title": data.loc[index, "title"],
                "genres": data.loc[index, "genres"],
                "overview": data.loc[index, "overview"],
                "vote_average": data.loc[index, "vote_average"],
                "poster_path": data.loc[index, "poster_path"],
                "language": data.loc[index, "language"],
                "industry": data.loc[index, "industry"],
                "favorite_score": favorite_scores[index],
                "history_score": history_scores[index],
                "genre_score": genre_scores[index],
                "final_score": score,
                "reason": reason,
            }
        )

    return pd.DataFrame(candidates).sort_values(["final_score", "vote_average"], ascending=False).head(top_n)


def show_reason(reason: RecommendationReason, score: float) -> None:
    st.caption(f"Similarity Score: {score * 100:.0f}%")
    lines = []
    if reason.favorite_match:
        lines.append(f"Similar to favorite movie: {reason.favorite_match}")
    if reason.history_match:
        lines.append(f"Similar to recently watched movie: {reason.history_match}")
    if reason.genre_match:
        lines.append("Matches current genre preference")
    if reason.shared_director:
        lines.append(f"Related director preference: {reason.shared_director}")
    if reason.shared_cast:
        lines.append(f"Shares cast preference: {reason.shared_cast}")
    if not lines:
        lines.append("Recommended using selected genre, language, industry, and rating")
    for line in lines[:4]:
        st.write(f"- {line}")


def render_movie_card(row: pd.Series, api_key: str) -> None:
    poster_url = tmdb_poster_url(row["poster_path"], api_key) or tmdb_search_poster(row["title"], api_key)
    left, right = st.columns([1, 3], vertical_alignment="top")
    with left:
        if poster_url:
            st.image(poster_url, use_container_width=True)
        else:
            st.markdown("**No poster**")
    with right:
        st.subheader(row["title"])
        st.write(f"**Genre:** {row['genres']}")
        st.write(f"**Language/Industry:** {row['language']} - {row['industry']}")
        st.write(f"**Rating:** {row['vote_average']:.1f}")
        st.write(row["overview"])
        show_reason(row["reason"], row["final_score"])


def render_search_result(data: pd.DataFrame, query: str, api_key: str) -> None:
    if not query:
        return
    matches = data[data["title"].str.contains(query, case=False, na=False)].head(5)
    if matches.empty:
        st.warning("No matching movie found in the current dataset.")
        return
    st.markdown("### Search Results")
    for _, movie in matches.iterrows():
        poster_url = tmdb_poster_url(movie["poster_path"], api_key) or tmdb_search_poster(movie["title"], api_key)
        with st.container(border=True):
            left, right = st.columns([1, 4], vertical_alignment="top")
            with left:
                if poster_url:
                    st.image(poster_url, use_container_width=True)
            with right:
                st.markdown(f"**{movie['title']}**")
                st.write(f"Genre: {movie['genres']}")
                st.write(f"Language/Industry: {movie['language']} - {movie['industry']}")
                st.write(f"Rating: {movie['vote_average']:.1f}")
                st.write(movie["overview"])


def main() -> None:
    st.set_page_config(page_title="Movie Recommendation System", layout="wide")
    st.title("Intelligent Personalized Movie Recommendation System")
    st.caption("Content-Based Filtering + User Preference Analysis + Weighted Recommendation Scoring")

    with st.sidebar:
        st.header("Dataset")
        uploaded_file = st.file_uploader("Upload custom movie CSV", type=["csv"])
        api_key = st.text_input("TMDB API Key for posters", value=os.getenv("TMDB_API_KEY", ""), type="password")
        top_n = st.slider("Number of recommendations", min_value=5, max_value=20, value=10)

    data = load_dataset(uploaded_file)
    _, similarity = build_similarity(data)

    st.markdown("### User Preference Input")
    col1, col2, col3 = st.columns(3)
    with col1:
        favorite_raw = st.text_area(
            "Favorite Movies",
            value="Interstellar\nInception\nOppenheimer",
            height=130,
            help="Enter one movie per line or separate using commas.",
        )
    with col2:
        watched_raw = st.text_area(
            "Previously Watched Movies",
            value="Tenet\nThe Dark Knight",
            height=130,
            help="Enter one movie per line or separate using commas.",
        )
    with col3:
        selected_genre = st.selectbox("Current Preferred Genre", GENRES, index=2)
        selected_language = st.selectbox("Language you want to watch", LANGUAGE_OPTIONS, index=0)
        selected_industry = st.selectbox("Movie industry", INDUSTRY_OPTIONS, index=0)

    search_query = st.text_input("Search Movie")
    render_search_result(data, search_query, api_key)

    favorite_movies = split_user_movies(favorite_raw)
    watched_movies = split_user_movies(watched_raw)
    known_inputs = find_movie_indices(data, favorite_movies + watched_movies)

    if not known_inputs:
        st.warning("No exact movie input matched the dataset. Showing recommendations using genre, language, and industry.")

    recommendations = recommend(
        data,
        similarity,
        favorite_movies,
        watched_movies,
        selected_genre,
        selected_language,
        selected_industry,
        top_n=top_n,
    )

    st.markdown("### Top Recommendations")
    if recommendations.empty:
        st.warning("No recommendations found for this language/industry filter. Try selecting Any or another genre.")
        return
    st.info(
        "Final Score = 0.4 * Favorite Movie Similarity + "
        "0.3 * Watch History Similarity + 0.3 * Genre Match"
    )

    for _, row in recommendations.iterrows():
        with st.container(border=True):
            render_movie_card(row, api_key)


if __name__ == "__main__":
    main()
