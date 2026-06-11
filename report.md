# Intelligent Personalized Movie Recommendation System Using Content-Based Filtering and User Preference Analysis

## 1. Introduction

Recommendation systems help users discover relevant items from large collections. This project recommends movies by analyzing movie content and user preferences such as favorite movies, recently watched movies, current genre interest, preferred language, and preferred movie industry.

## 2. Problem Statement

Users often spend time searching for movies that match their taste. The goal is to build an intelligent system that recommends movies using movie metadata and user preference inputs.

## 3. Objectives

- Build a content-based movie recommendation system.
- Use TF-IDF vectorization to convert movie features into numerical vectors.
- Use cosine similarity to compare movies.
- Combine favorite movies, watch history, genre preference, language preference, and industry preference.
- Provide explainable recommendations through similarity scores and reasons.

## 4. Literature Survey

Movie recommendation systems are commonly built using collaborative filtering, content-based filtering, or hybrid approaches. Collaborative filtering requires user interaction data, such as ratings from many users. Content-based filtering works with item metadata, making it suitable when user-user interaction data is unavailable.

## 5. System Architecture

```text
User Input
  |
Favorite Movies + Watched Movies + Current Genre
  |
Feature Engineering
  |
TF-IDF Vectorization
  |
Cosine Similarity
  |
Weighted Scoring
  |
Top 10 Movie Recommendations
```

## 6. Dataset Description

The project uses the public MovieLens dataset from GroupLens for Hollywood/English movies and a regional movie CSV for Indian industries. The final dataset includes title, genres, overview, cast, director, keywords, vote_average, language, and industry columns. Supported industries include Hollywood, Bollywood, Tollywood, Sandalwood, Kollywood, and Mollywood.

## 7. Methodology

### Data Preprocessing

Missing values are replaced with empty strings. Ratings are converted into numeric values. Text fields are normalized before vectorization.

### Feature Engineering

A combined tag field is created by merging important movie attributes:

```text
tags = genres + cast + director + keywords + overview
```

### Vectorization

TF-IDF vectorization converts the combined tags into numerical vectors.

### Similarity Calculation

Cosine similarity calculates similarity between all movies.

### Weighted Recommendation Scoring

The final recommendation score is calculated as:

```text
Final Score = 0.4 * Favorite Movie Similarity
            + 0.3 * Watch History Similarity
            + 0.3 * Genre Match
```

This formula combines long-term preference, recent interest, and current mood.

After calculating the score, the system filters recommendations by the selected language and industry. For example, if the user selects Telugu and Tollywood, only Telugu/Tollywood movies are displayed.

## 8. Algorithms Used

- TF-IDF Vectorization
- Cosine Similarity
- Content-Based Filtering
- Weighted Recommendation Scoring

## 9. Results

The system displays the top 10 recommended movies with movie title, genre, rating, similarity score, description, and explanation. Example explanations include similarity to selected movies, genre match, and director/cast relationship.

## 10. Future Scope

- Add more regional movies from authenticated Kaggle or TMDB API sources.
- Improve poster and metadata quality using the TMDB API.
- Add user login and save preference history.
- Add sentiment analysis on movie reviews.
- Deploy the Streamlit app online.

## 11. Conclusion

The project successfully demonstrates a personalized movie recommendation system using content-based filtering and user preference analysis. The weighted scoring method makes the system more flexible than simple content similarity by combining long-term preferences, recent behavior, and current genre mood.

## Viva Preparation

**What type of recommendation system is this?**  
It is a content-based recommendation system with hybrid-style weighted user preference analysis.

**Why not collaborative filtering?**  
Collaborative filtering requires user-user or user-item interaction data, which is not available in this dataset.

**What is TF-IDF?**  
TF-IDF is a technique that converts text into numerical vectors based on term importance.

**What is cosine similarity?**  
Cosine similarity measures the similarity between two vectors based on the angle between them.

**Why use weighted scoring?**  
Weighted scoring combines long-term favorites, recently watched movies, and current genre mood into one final recommendation score.
