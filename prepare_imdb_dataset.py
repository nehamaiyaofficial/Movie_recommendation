from __future__ import annotations

import gzip
import shutil
import urllib.request
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
IMDB_DIR = DATA_DIR / "imdb"
OUTPUT_PATH = DATA_DIR / "imdb_movies_clean.csv"
START_YEAR = 1990

FILES = {
    "basics": "https://datasets.imdbws.com/title.basics.tsv.gz",
    "akas": "https://datasets.imdbws.com/title.akas.tsv.gz",
    "ratings": "https://datasets.imdbws.com/title.ratings.tsv.gz",
}

LANGUAGE_MAP = {
    "hi": ("Hindi", "Bollywood"),
    "te": ("Telugu", "Tollywood"),
    "kn": ("Kannada", "Sandalwood"),
    "ta": ("Tamil", "Kollywood"),
    "ml": ("Malayalam", "Mollywood"),
    "en": ("English", "Hollywood"),
}

REGION_FALLBACK = {
    "US": ("English", "Hollywood"),
    "GB": ("English", "Hollywood"),
    "IN": ("Hindi", "Bollywood"),
}


def download_file(url: str, target: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def read_tsv_gz(path: Path, usecols: list[str]) -> pd.DataFrame:
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return pd.read_csv(file, sep="\t", usecols=usecols, na_values="\\N", low_memory=False)


def download_imdb_files() -> None:
    for name, url in FILES.items():
        download_file(url, IMDB_DIR / f"{name}.tsv.gz")


def classify_akas(akas: pd.DataFrame) -> pd.DataFrame:
    akas = akas[akas["titleId"].notna()].copy()
    akas["language"] = akas["language"].fillna("")
    akas["region"] = akas["region"].fillna("")

    rows = []
    for code, (language, industry) in LANGUAGE_MAP.items():
        selected = akas[akas["language"].str.lower() == code][["titleId"]].copy()
        selected["language"] = language
        selected["industry"] = industry
        rows.append(selected)

    for region, (language, industry) in REGION_FALLBACK.items():
        selected = akas[(akas["region"] == region) & (akas["language"] == "")][["titleId"]].copy()
        selected["language"] = language
        selected["industry"] = industry
        rows.append(selected)

    classified = pd.concat(rows, ignore_index=True).drop_duplicates(subset=["titleId"])
    return classified


def build_imdb_dataset() -> pd.DataFrame:
    basics = read_tsv_gz(
        IMDB_DIR / "basics.tsv.gz",
        ["tconst", "titleType", "primaryTitle", "startYear", "genres", "isAdult"],
    )
    ratings = read_tsv_gz(IMDB_DIR / "ratings.tsv.gz", ["tconst", "averageRating", "numVotes"])
    akas = read_tsv_gz(IMDB_DIR / "akas.tsv.gz", ["titleId", "region", "language"])

    basics["startYear"] = pd.to_numeric(basics["startYear"], errors="coerce")
    basics = basics[
        (basics["titleType"] == "movie")
        & (basics["isAdult"].astype(str) == "0")
        & (basics["startYear"] >= START_YEAR)
    ].copy()

    classified = classify_akas(akas)
    data = basics.merge(classified, left_on="tconst", right_on="titleId", how="inner")
    data = data.merge(ratings, on="tconst", how="left")
    data["vote_average"] = pd.to_numeric(data["averageRating"], errors="coerce").fillna(0)
    data["numVotes"] = pd.to_numeric(data["numVotes"], errors="coerce").fillna(0)
    data = data.sort_values(["numVotes", "vote_average"], ascending=False)

    data["genres"] = data["genres"].fillna("").str.replace(",", " ", regex=False)
    data["title"] = data["primaryTitle"].fillna("")
    data["overview"] = (
        data["title"]
        + " is a "
        + data["language"]
        + " "
        + data["genres"]
        + " movie released in "
        + data["startYear"].astype("Int64").astype(str)
        + "."
    )
    data["cast"] = ""
    data["director"] = ""
    data["keywords"] = data["genres"] + " " + data["language"] + " " + data["industry"]
    data["poster_path"] = ""

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
    return data[columns].drop_duplicates(subset=["title", "language", "industry"]).reset_index(drop=True)


def main() -> None:
    download_imdb_files()
    data = build_imdb_dataset()
    data.to_csv(OUTPUT_PATH, index=False)
    print(f"Created {OUTPUT_PATH} with {len(data)} movies from IMDb public datasets.")


if __name__ == "__main__":
    main()
