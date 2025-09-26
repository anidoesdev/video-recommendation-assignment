from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pandas as pd 

from app.services.data_fetcher import get_user_profile_data, fetch_all_posts
from app.recommendations.deep_recommender import (
    build_deep_similarity_matrix,
    get_deep_recommendation,
    get_popular_posts
)
app = FastAPI(
    title="Video Recommendation API",
    description="An API that serves personalized video recommendations."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

all_posts: pd.DataFrame = pd.DataFrame()
deep_recommender = None

@app.on_event("startup")
def load_model_and_data():
    global all_posts, deep_recommender
    print("Loading all post data...")
    all_posts = fetch_all_posts()
    if not all_posts.empty:
        print("Building deep learning model and embeddings...")
        deep_recommender = build_deep_similarity_matrix(all_posts)
        print("Startup Complete. Deep learning model and data are ready")
    else:
        print("Error: Could not fetch post data on startup.")

@app.get("/health", tags=["System"])
async def health() -> dict:
    ready = not all_posts.empty and deep_recommender is not None
    return {
        "ready": ready,
        "posts_cached": int(len(all_posts)) if isinstance(all_posts, pd.DataFrame) else 0,
        "model_loaded": deep_recommender is not None,
        "model_name": deep_recommender.model_name if deep_recommender else None
    }

@app.get("/feed", tags=["Recommendations"])
async def get_personalized_feed(username: str, project_code: Optional[str] = None, page: int = 1, page_size: int = 20):
    if all_posts.empty or deep_recommender is None:
        raise HTTPException(status_code=503, detail="Service is not ready, data not loaded")
    
    user_profile = get_user_profile_data(username=username)
    
    print(user_profile)
    recommended_ids = []
    
    if user_profile.empty:
        print(f"Cold start: No profile found for user '{username}'. Returning popular posts.")
        recommended_ids = get_popular_posts(all_posts)
    else:
        print(f"Generating personalized feed for user '{username}' using deep learning... ")
        recommended_ids = get_deep_recommendation(
            username=username,
            user_profile_df=user_profile,
            all_post_df=all_posts,
            deep_recommender=deep_recommender
        )
    
    if not recommended_ids:
        return {"recommendations": []}
    
    results_df = all_posts[all_posts["id"].isin(recommended_ids)].copy()
    
    if project_code:
        def check_project_code(topic):
            return isinstance(topic,dict) and topic.get('project_code') == project_code
        results_df = results_df[results_df['topic'].apply(check_project_code)]
    
    # stable order by view_count desc as a proxy, or maintain order of recommended_ids
    results_df = results_df.sort_values(by='view_count', ascending=False, na_position='last')

    # pagination
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    start = (page - 1) * page_size
    end = start + page_size
    paged_df = results_df.iloc[start:end]

    recommendations = paged_df.to_dict('records')

    return {"recommendations": recommendations, "page": page, "page_size": page_size, "total": int(len(results_df))}


@app.get("/similar/{post_id}", tags=["Recommendations"])
async def get_similar_posts(post_id: int, top_k: int = 10):
    """
    Get posts similar to a given post using deep learning embeddings.
    
    Args:
        post_id: ID of the reference post
        top_k: Number of similar posts to return (default: 10)
    """
    if all_posts.empty or deep_recommender is None:
        raise HTTPException(status_code=503, detail="Service is not ready, data not loaded")
    
    try:
        similar_posts = deep_recommender.get_similar_posts(post_id, top_k)
        
        if not similar_posts:
            return {"similar_posts": [], "reference_post_id": post_id}
        
        # Get post details for similar posts
        similar_post_ids = [post_id for post_id, _ in similar_posts]
        similar_posts_df = all_posts[all_posts["id"].isin(similar_post_ids)].copy()
        
        # Add similarity scores
        similarity_scores = {post_id: score for post_id, score in similar_posts}
        similar_posts_df['similarity_score'] = similar_posts_df['id'].map(similarity_scores)
        
        # Sort by similarity score
        similar_posts_df = similar_posts_df.sort_values('similarity_score', ascending=False)
        
        similar_posts_data = similar_posts_df.to_dict('records')
        
        return {
            "similar_posts": similar_posts_data,
            "reference_post_id": post_id,
            "count": len(similar_posts_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found or error occurred: {str(e)}")