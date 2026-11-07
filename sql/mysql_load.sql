-- MySQL 8 schema and load script for the processed Netflix tables.
-- Run from the repository root (local_infile must be enabled on the server and client):
--   mysql --local-infile=1 -u <user> -p < sql/mysql_load.sql
-- Then point the dashboard at MySQL with NETFLIX_SOURCE=mysql (see app/app.py).

CREATE DATABASE IF NOT EXISTS netflix_db;
USE netflix_db;

DROP TABLE IF EXISTS title_genres;
DROP TABLE IF EXISTS titles;

CREATE TABLE titles (
    show_id            VARCHAR(10)  NOT NULL PRIMARY KEY,
    title              VARCHAR(300),
    type               VARCHAR(10),
    primary_country    VARCHAR(80),
    n_countries        INT,
    release_year       INT,
    date_added         DATE NULL,
    year_added         INT NULL,
    rating             VARCHAR(20),
    audience           VARCHAR(20),
    rating_repaired    VARCHAR(5),
    duration_value     INT NULL,
    duration_unit      VARCHAR(10),
    content_age        INT NULL,
    content_age_group  VARCHAR(30),
    release_decade     INT NULL,
    is_recent          TINYINT,
    add_lag_years      INT NULL,
    is_original_window TINYINT NULL,
    genre_count        INT,
    INDEX idx_type (type), INDEX idx_year_added (year_added), INDEX idx_country (primary_country)
);

CREATE TABLE title_genres (
    show_id         VARCHAR(10) NOT NULL,
    genre           VARCHAR(60) NOT NULL,
    type            VARCHAR(10),
    year_added      INT NULL,
    release_year    INT NULL,
    primary_country VARCHAR(80),
    PRIMARY KEY (show_id, genre),
    FOREIGN KEY (show_id) REFERENCES titles (show_id)
);

LOAD DATA LOCAL INFILE 'data/processed/titles.csv' INTO TABLE titles
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES
    (show_id, title, type, primary_country, n_countries, @release_year, @date_added, @year_added, rating, audience, rating_repaired,
     @duration_value, duration_unit, @content_age, content_age_group, @release_decade, is_recent, @add_lag_years, @is_original_window, genre_count)
    SET release_year = NULLIF(@release_year, ''), date_added = NULLIF(@date_added, ''), year_added = NULLIF(@year_added, ''),
        duration_value = NULLIF(@duration_value, ''), content_age = NULLIF(@content_age, ''), release_decade = NULLIF(@release_decade, ''),
        add_lag_years = NULLIF(@add_lag_years, ''), is_original_window = NULLIF(@is_original_window, '');

LOAD DATA LOCAL INFILE 'data/processed/title_genres.csv' INTO TABLE title_genres
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES
    (show_id, genre, type, @year_added, @release_year, primary_country)
    SET year_added = NULLIF(@year_added, ''), release_year = NULLIF(@release_year, '');

-- KPI queries: see sql/kpi_queries.sql (portable between MySQL and SQLite).
