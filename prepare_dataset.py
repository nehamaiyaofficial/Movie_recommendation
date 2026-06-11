from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
ZIP_PATH = DATA_DIR / "ml-latest-small.zip"
EXTRACT_DIR = DATA_DIR / "ml-latest-small"
OUTPUT_PATH = DATA_DIR / "movies_clean.csv"
REGIONAL_PATH = DATA_DIR / "indian_movies.csv"
IMDB_PATH = DATA_DIR / "imdb_movies_clean.csv"


def extract_dataset() -> None:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(
            "MovieLens zip file not found. Download it from "
            "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip "
            "and place it at data/ml-latest-small.zip."
        )

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        archive.extractall(DATA_DIR)


def clean_title(title: str) -> str:
    return str(title).strip()


def build_clean_dataset() -> pd.DataFrame:
    movies_path = EXTRACT_DIR / "movies.csv"
    ratings_path = EXTRACT_DIR / "ratings.csv"
    tags_path = EXTRACT_DIR / "tags.csv"

    movies = pd.read_csv(movies_path)
    ratings = pd.read_csv(ratings_path)
    tags = pd.read_csv(tags_path)

    rating_summary = (
        ratings.groupby("movieId")["rating"]
        .mean()
        .reset_index()
        .rename(columns={"rating": "vote_average"})
    )
    tag_summary = (
        tags.groupby("movieId")["tag"]
        .apply(lambda values: " ".join(sorted({str(value).strip() for value in values if str(value).strip()})))
        .reset_index()
        .rename(columns={"tag": "keywords"})
    )

    data = movies.merge(rating_summary, on="movieId", how="left").merge(tag_summary, on="movieId", how="left")
    data["title"] = data["title"].apply(clean_title)
    data["genres"] = data["genres"].str.replace("|", " ", regex=False).replace("(no genres listed)", "")
    data["keywords"] = data["keywords"].fillna("")
    data["overview"] = (
        "Movie with genres "
        + data["genres"].fillna("")
        + ". User tags: "
        + data["keywords"].fillna("")
    )
    data["cast"] = ""
    data["director"] = ""
    data["poster_path"] = ""
    data["vote_average"] = (data["vote_average"].fillna(data["vote_average"].mean()) * 2).round(2)
    data["language"] = "English"
    data["industry"] = "Hollywood"

    columns = [
        "title",
        "genres",
        "overview",
        "cast",
        "director",
        "keywords",
        "vote_average",
        "poster_path",
        "language",
        "industry",
    ]
    clean_data = data[columns]

    if REGIONAL_PATH.exists():
        regional_data = pd.read_csv(REGIONAL_PATH)
        for column in columns:
            if column not in regional_data.columns:
                regional_data[column] = ""
        clean_data = pd.concat([regional_data[columns], clean_data], ignore_index=True)

    if IMDB_PATH.exists():
        imdb_data = pd.read_csv(IMDB_PATH)
        for column in columns:
            if column not in imdb_data.columns:
                imdb_data[column] = ""
        clean_data = pd.concat([imdb_data[columns], clean_data], ignore_index=True)

    return clean_data.drop_duplicates(subset=["title", "language", "industry"]).reset_index(drop=True)


def main() -> None:
    extract_dataset()
    clean_data = build_clean_dataset()
    clean_data.to_csv(OUTPUT_PATH, index=False)
    print(f"Created {OUTPUT_PATH} with {len(clean_data)} movies.")


if __name__ == "__main__":
    main()
