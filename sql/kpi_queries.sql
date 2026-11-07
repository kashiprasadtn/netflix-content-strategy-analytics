-- Portable KPI queries (MySQL 8 and SQLite) over the processed tables.
-- titles        : one row per title
-- title_genres  : one row per title x genre
-- Each query is preceded by a "name" marker line so the analysis notebook can run and validate it.

-- name: kpi_summary
SELECT COUNT(*)                                            AS total_titles,
       SUM(CASE WHEN type = 'Movie'   THEN 1 ELSE 0 END)   AS movies,
       SUM(CASE WHEN type = 'TV Show' THEN 1 ELSE 0 END)   AS tv_shows,
       ROUND(AVG(content_age), 1)                          AS avg_content_age,
       ROUND(AVG(is_recent), 3)                            AS recent_share,
       COUNT(DISTINCT CASE WHEN primary_country <> 'Unknown' THEN primary_country END) AS countries
FROM titles;

-- name: titles_added_by_year
SELECT year_added, type, COUNT(*) AS title_count
FROM titles
WHERE year_added BETWEEN 2015 AND 2021
GROUP BY year_added, type
ORDER BY year_added, type;

-- name: freshness_by_year
SELECT year_added,
       ROUND(AVG(is_original_window), 3)                         AS share_added_within_1y,
       ROUND(AVG(CASE WHEN add_lag_years >= 10 THEN 1.0 ELSE 0 END), 3) AS share_10y_plus
FROM titles
WHERE year_added BETWEEN 2015 AND 2021
GROUP BY year_added
ORDER BY year_added;

-- name: top_genres
SELECT genre, COUNT(DISTINCT show_id) AS title_count
FROM title_genres
GROUP BY genre
ORDER BY title_count DESC
LIMIT 12;

-- name: top_countries
SELECT primary_country, COUNT(*) AS title_count
FROM titles
WHERE primary_country <> 'Unknown'
GROUP BY primary_country
ORDER BY title_count DESC
LIMIT 10;

-- name: audience_mix
SELECT type, audience, COUNT(*) AS title_count
FROM titles
GROUP BY type, audience
ORDER BY type, title_count DESC;

-- name: grain_trap
-- Joining titles to genres multiplies rows: COUNT(*) overstates the catalogue, COUNT(DISTINCT) does not.
SELECT COUNT(*) AS naive_rows, COUNT(DISTINCT t.show_id) AS distinct_titles
FROM titles t JOIN title_genres g ON t.show_id = g.show_id;
