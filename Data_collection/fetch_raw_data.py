import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import os

import requests
from dotenv import load_dotenv

load_dotenv()

APPLIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_APPREVIEWS_URL = "https://store.steampowered.com/appreviews/"
STEAMSPY_URL = "https://steamspy.com/api.php"


def get_app_list(max_results: int = 1000) -> List[Dict[str, Any]]:
    '''
    Call the Steam IStoreService/GetAppList endpoint and return
    a list of app records (each record contains at least appid and name).
    The result is limited by max_results.
    '''
    api_key = os.environ["STEAM_API_KEY"]

    params = {
        "key": api_key,
        "include_games": True,
        "include_dlc": False,
        "include_software": False,
        "include_videos": False,
        "include_hardware": False,
        "max_results": max_results,
    }

    resp = requests.get(APPLIST_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    apps = data.get("response", {}).get("apps", [])
    return apps


def get_sample_app_ids(max_games: int = 300) -> List[int]:
    '''
    Use get_app_list to obtain a batch of apps and extract appid values.
    Return at most max_games appids as the sample frame for later calls.
    '''
    apps = get_app_list(max_results=max_games)
    app_ids = [app["appid"] for app in apps if app.get("appid")]
    return app_ids


def fetch_app_details(app_id: int) -> Optional[Dict[str, Any]]:
    '''
    Fetch detailed information for a single app from the Storefront
    appdetails endpoint. Only return data if the type is "game".
    Otherwise return None.
    '''
    params = {"appids": app_id, "cc": "us", "l": "en"}
    resp = requests.get(STEAM_APPDETAILS_URL, params=params, timeout=20)
    if resp.status_code != 200:
        return None

    raw = resp.json()
    entry = raw.get(str(app_id))
    if not entry or not entry.get("success"):
        return None

    data = entry.get("data", {})
    if data.get("type") != "game":
        return None

    return data


def fetch_review_summary(app_id: int) -> Optional[Dict[str, Any]]:
    '''
    Fetch aggregated review statistics for a single app from the
    /appreviews endpoint. Return the query_summary block, which
    contains total_reviews and total_positive, or None on failure.
    '''
    params = {
        "json": 1,
        "language": "all",
        "purchase_type": "all",
        "num_per_page": 0,
    }
    resp = requests.get(f"{STEAM_APPREVIEWS_URL}{app_id}", params=params, timeout=20)
    if resp.status_code != 200:
        return None

    data = resp.json()
    return data.get("query_summary")


def fetch_owners_proxy(app_id: int) -> Optional[int]:
    '''
    Query the SteamSpy appdetails API for a single app and use the
    reported owners range as a proxy for sales. The function returns
    the midpoint of the owners interval as an integer, or None if the
    value is not available or cannot be parsed.
    '''
    params = {"request": "appdetails", "appid": app_id}
    try:
        resp = requests.get(STEAMSPY_URL, params=params, timeout=20)
        if resp.status_code != 200:
            return None

        data = resp.json()
        owners_str = data.get("owners")
        if not owners_str:
            return None

        cleaned = owners_str.replace(",", "").replace(" ", "")
        parts = cleaned.split("..")
        if len(parts) != 2:
            return None

        low = int(parts[0])
        high = int(parts[1])
        return (low + high) // 2

    except (ValueError, TypeError) as e:
        print(f"SteamSpy parse error for app {app_id}: {e}")
        return None
    except Exception as e:
        print(f"SteamSpy error for app {app_id}: {e}")
        return None


def fetch_and_save_raw_data(output_path: str, max_games: int = 300) -> None:
    '''
    Orchestrate the full data collection pipeline:
    1) sample a set of appids,
    2) fetch appdetails, review summaries, and owners proxy for each app,
    3) assemble the fields into a list of dictionaries,
    4) save the resulting list as a JSON file at output_path.
    '''
    snapshot_time = datetime.utcnow().isoformat() + "Z"

    app_ids = get_sample_app_ids(max_games=max_games)
    results: List[Dict[str, Any]] = []

    for idx, app_id in enumerate(app_ids, start=1):
        try:
            details = fetch_app_details(app_id)
            if not details:
                continue

            reviews = fetch_review_summary(app_id)
            total_reviews = None
            positive_reviews = None
            if reviews:
                total_reviews = reviews.get("total_reviews")
                positive_reviews = reviews.get("total_positive")

            owners_proxy = fetch_owners_proxy(app_id)

            price = details.get("price_overview") or {}
            original_price = price.get("initial")
            current_price = price.get("final")

            genres = details.get("genres") or []
            genre_list = [g.get("description") for g in genres if g.get("description")]

            row = {
                "app_id": app_id,
                "name": details.get("name"),
                "release_date": details.get("release_date", {}).get("date"),
                "original_price_cents": original_price,
                "current_price_cents": current_price,
                "is_free": details.get("is_free"),
                "genres": genre_list,
                "total_reviews": total_reviews,
                "positive_reviews": positive_reviews,
                "owners_proxy": owners_proxy,
                "snapshot_time": snapshot_time,
                "raw_appdetails": details,
                "raw_review_summary": reviews,
            }

            results.append(row)

            if idx % 50 == 0:
                print(f"Fetched {idx} apps...")
            time.sleep(0.3)

        except Exception as e:
            print(f"Error on app_id={app_id}: {e}")
            continue

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(results)} records to {output_path}")
