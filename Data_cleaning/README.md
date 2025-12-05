#### 1. Data Sources and Collection
* **Source:** Data was collected primarily from public Steam Web APIs (e.g., app details, review summaries) and the SteamSpy API.

* **Methodology:** We sampled a list of App IDs via the Steam API. For each ID, we performed subsequent calls to fetch detailed game information, aggregate review statistics, and a sales proxy (owners_proxy). All collected data was timestamped (snapshot_time) and stored as JSON (Rawdata/games_raw.json).

#### 2. Data Cleaning and Filtering
To ensure data quality for modeling, the following filtering criteria were applied:

* **Completeness Check:** Records were dropped if they were missing values for critical features: release_date, total_reviews, owners_proxy, or original_price_cents.

* **Minimum Review Threshold:** Games with fewer than 50 total reviews were excluded. This ensures that calculated review metrics are based on a stable sample size.

* **Type Filtering:** The collection process was designed to only retrieve records classified as "game", excluding other content types like software or DLC.

#### 3. Final Dataset Structure and Variables

The resulting `games_clean.csv` file contains the following selected variables, including both original fields retained from the API and new engineered features:

| Variable Name | Type | Source/Construction | Purpose/Meaning |
| :--- | :--- | :--- | :--- |
| **`app_id`** | Integer | Original API | Unique identifier for the game on Steam. |
| **`name`** | String | Original API | Title of the game. |
| **`release_date`** | String | Original API | Date the game was released (Used for time calculation). |
| **`total_reviews`** | Integer | Original API | Total number of reviews (Used as review count filter). |
| **`owners_proxy`** | Integer | Original API (SteamSpy) | Midpoint of the estimated ownership range (sales proxy). |
| **`original_price_usd`**| Float | Calculated | Original price converted from cents to US Dollars. |
| **`current_price_usd`**| Float | Calculated | Current price converted from cents to US Dollars. |
| **`is_free`** | Integer (0/1) | Calculated | Binary indicator (0=Paid, 1=Free-to-Play). |
| **`review_ratio`** | Float | **Engineered** | `positive_reviews / total_reviews`. Standardized measure of player satisfaction. |
| **`days_since_release`** | Integer | **Engineered** | Time elapsed (in days) between release date and data snapshot. Measures market age. |
| **`main_genre`**** | String | **Engineered** | Primary genre extracted from the `genres` list. |

#### 4. Data Limitations and Extensions

* **Data Limitations:** The `owners_proxy` variable is based on ranges reported by SteamSpy and is an estimate, not a direct sales figure. Furthermore, the dataset represents a single snapshot in time, missing insights into sales over time or seasonal trends.
* **Extensions:** Future work could involve collecting additional data, such as detailed user tags, full-text review content , or using an updated collection schedule to enable time-series analysis of price changes and review decay.
