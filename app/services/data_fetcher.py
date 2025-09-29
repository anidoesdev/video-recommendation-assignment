import os 
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
FLIC_TOKEN = os.getenv("FLIC_TOKEN")

INTERACTION_SCORES = {
    "view": 1.0,
    "like": 4.0,
    "inspire": 5.0
}

def _get_with_retries(url: str, headers: dict, timeout: float = 10.0, retries: int = 2, backoff: float = 0.5):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
            else:
                break
    raise last_exc

def fetch_user_interactions(interaction_type: str, username: str) -> list:
    url = f"{API_BASE_URL}/posts/{interaction_type}?username={username}&page=1&page_size=1000&resonance_algorithm=resonance_algorithm_cjsvervb7dbhss8bdrj89s44jfjdbsjd0xnjkbvuire8zcjwerui3njfbvsujc5if"
    headers = {"Flic-Token": FLIC_TOKEN}
    try:
        response = _get_with_retries(url, headers=headers)
        data = response.json()
        return data.get("posts", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {interaction_type} data for {username}: {e}")
        return []
    
def get_user_profile_data(username: str) -> pd.DataFrame:
    all_interactions = []
    
    for interaction, score in INTERACTION_SCORES.items():
        posts = fetch_user_interactions(interaction_type=interaction, username=username)
        for post in posts:
            all_interactions.append({
                "username": username,
                "post_id": post.get("id"),
                "interaction_score": score
            })
    
    rated_posts = fetch_user_interactions(interaction_type="rating", username=username)
    for post in rated_posts:
        rating_score = post.get("average_rating",0) / 10.0
        if rating_score > 0:
            all_interactions.append({
                "username": username,
                "post_id": post.get("id"),
                "interaction_score": rating_score
            })
    if not all_interactions:
        return pd.DataFrame(columns=["username","post_id","interaction_score"])
    
    df = pd.DataFrame(all_interactions)
    
    df = df.groupby(['username','post_id']).max().reset_index()
    
    return df

def fetch_all_posts() -> pd.DataFrame:
    url = f"{API_BASE_URL}/posts/summary/get?page=1&page_size=1000"
    headers = {"Flic-Token": FLIC_TOKEN}
    try:
        response = _get_with_retries(url, headers=headers)
        data = response.json().get("posts", [])
        return pd.DataFrame(data)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching all posts: {e}")
        return pd.DataFrame()
        

# if __name__ == "__main__":
#     test_username = "afrobeezy"
    
#     print(f"Fetching profile for user: {test_username}...")
#     user_df = get_user_profile_data(test_username)
    
#     if not user_df.empty:
#         print("Successfully created user profile DataFrame:")
#         print(user_df.head())
#         print(f"\nFound {len(user_df)} total unique interactions.")
#     else:
#         print(f"No interaction data found for user '{test_username}'.")