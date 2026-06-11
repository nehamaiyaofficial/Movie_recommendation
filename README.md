# Intelligent Personalized Movie Recommendation System

Hybrid personalized movie recommender using content-based filtering, user preference analysis, TF-IDF vectorization, cosine similarity, and weighted scoring.

## Features

- Favorite movie based recommendations
- Previously watched movie based recommendations
- Current genre preference
- Language preference such as English, Hindi, Telugu, Kannada, Tamil, and Malayalam
- Industry preference such as Hollywood, Bollywood, Tollywood, Sandalwood, Kollywood, and Mollywood
- Weighted recommendation formula:

```text
Final Score = 0.4 * Favorite Similarity + 0.3 * Watch History Similarity + 0.3 * Genre Match
```

- Explainable recommendation output
- Search bar for instant movie lookup
- Optional TMDB poster support using an API key
- Streamlit frontend

## Project Structure

```text
.
|-- app.py
|-- data/
|   |-- ml-latest-small.zip
|   |-- indian_movies.csv
|   |-- movies_clean.csv
|   `-- sample_movies.csv
|-- prepare_dataset.py
|-- report.md
|-- requirements.txt
`-- README.md
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Download used in this project:

```text
https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
```

Prepare the downloaded MovieLens dataset:

```bash
python prepare_dataset.py
```

Run the app:

```bash
streamlit run app.py
```

## Dataset

The project uses the public MovieLens `ml-latest-small` dataset from GroupLens:

```text
https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
```

`prepare_dataset.py` converts MovieLens movies, ratings, and tags into `data/movies_clean.csv`, then merges regional Indian movie entries from `data/indian_movies.csv`. The final dataset supports language and industry filtering. A small sample dataset remains as a fallback.

Required or supported columns:

```text
title, genres, overview, cast, director, keywords, vote_average, poster_path, language, industry
```

`poster_path` is optional. If present and a TMDB API key is provided in the sidebar, posters are shown automatically.

## Viva Points

- This is a content-based recommendation system.
- TF-IDF converts movie text features into numerical vectors.
- Cosine similarity compares movie vectors.
- Weighted scoring combines long-term preference, recent behavior, and current mood.
- Language and industry filtering makes recommendations match what the user wants to watch now.
- Collaborative filtering is not used because user-user interaction data is not available.
