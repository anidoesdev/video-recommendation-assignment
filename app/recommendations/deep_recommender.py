import pandas as pd
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class DeepContentRecommender:
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "auto"):
        self.model_name = model_name
        self.device = self._get_device(device)
        self.model = None
        self.post_embeddings = None
        self.post_ids = None
        self.embedding_dim = None
        
        logger.info(f"Initializing DeepContentRecommender with model: {model_name}")
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use."""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            else:
                return "cpu"
        return device
    
    def load_model(self):
        """Load the pre-trained sentence transformer model."""
        try:
            logger.info(f"Loading model {self.model_name} on {self.device}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def prepare_content(self, all_posts_df: pd.DataFrame) -> List[str]:
        # Extract and clean text fields
        all_posts_df = all_posts_df.copy()
        all_posts_df['tags'] = all_posts_df['tags'].apply(
            lambda x: ' '.join(x) if isinstance(x, list) else str(x) if x else ''
        )
        all_posts_df['category_name'] = all_posts_df['category'].apply(
            lambda x: x.get('name', '') if isinstance(x, dict) else str(x) if x else ''
        )
        all_posts_df['topic_name'] = all_posts_df['topic'].apply(
            lambda x: x.get('name', '') if isinstance(x, dict) else str(x) if x else ''
        )
        
        # Combine all text fields
        content_strings = []
        for _, row in all_posts_df.iterrows():
            content_parts = [
                str(row.get('title', '')),
                str(row.get('tags', '')),
                str(row.get('category_name', '')),
                str(row.get('topic_name', ''))
            ]
            content = ' '.join(part for part in content_parts if part.strip())
            content_strings.append(content)
        
        return content_strings
    
    def build_embeddings(self, all_posts_df: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            self.load_model()
        
        logger.info("Building BERT embeddings for posts...")
        content_strings = self.prepare_content(all_posts_df)
        
        # Generate embeddings in batches for efficiency
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(content_strings), batch_size):
            batch = content_strings[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch, 
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            embeddings.append(batch_embeddings)
        
        self.post_embeddings = np.vstack(embeddings)
        self.post_ids = all_posts_df['id'].tolist()
        
        logger.info(f"Generated embeddings for {len(self.post_embeddings)} posts")
        return self.post_embeddings
    
    def get_user_profile_embedding(self, user_profile_df: pd.DataFrame, all_posts_df: pd.DataFrame) -> np.ndarray:
        if self.post_embeddings is None:
            raise ValueError("Post embeddings not built. Call build_embeddings() first.")
        
        # Map post IDs to embedding indices
        post_id_to_idx = {post_id: idx for idx, post_id in enumerate(self.post_ids)}
        
        user_embeddings = []
        user_weights = []
        
        for _, interaction in user_profile_df.iterrows():
            post_id = interaction['post_id']
            interaction_score = interaction['interaction_score']
            
            if post_id in post_id_to_idx:
                embedding_idx = post_id_to_idx[post_id]
                user_embeddings.append(self.post_embeddings[embedding_idx])
                user_weights.append(interaction_score)
        
        if not user_embeddings:
            logger.warning("No valid interactions found for user profile")
            return np.zeros(self.embedding_dim)
        
        # Weighted average of user's interacted post embeddings
        user_embeddings = np.array(user_embeddings)
        user_weights = np.array(user_weights)
        
        # Normalize weights
        user_weights = user_weights / np.sum(user_weights)
        
        user_profile = np.average(user_embeddings, axis=0, weights=user_weights)
        
        logger.info(f"Created user profile embedding from {len(user_embeddings)} interactions")
        return user_profile
    
    def get_recommendations(
        self, 
        username: str, 
        user_profile_df: pd.DataFrame, 
        all_posts_df: pd.DataFrame,
        top_k: int = 20,
        diversity_weight: float = 0.1
    ) -> List[int]:
        
        if self.post_embeddings is None:
            raise ValueError("Post embeddings not built. Call build_embeddings() first.")
        
        if user_profile_df.empty:
            logger.info(f"Cold start for user {username}")
            return self._get_popular_posts(all_posts_df, top_k)
        
        # Get user profile embedding
        user_profile = self.get_user_profile_embedding(user_profile_df, all_posts_df)
        
        # Calculate similarities between user profile and all posts
        similarities = cosine_similarity([user_profile], self.post_embeddings)[0]
        
        # Get interacted post IDs to exclude
        interacted_post_ids = set(user_profile_df['post_id'].tolist())
        
        # Create candidate scores
        candidate_scores = []
        for i, post_id in enumerate(self.post_ids):
            if post_id not in interacted_post_ids:
                # Base similarity score
                similarity_score = similarities[i]
                
                # Add popularity boost (log-scaled view count)
                post_data = all_posts_df[all_posts_df['id'] == post_id]
                if not post_data.empty:
                    view_count = post_data.iloc[0].get('view_count', 0)
                    popularity_boost = np.log1p(view_count) * 0.05
                else:
                    popularity_boost = 0
                
                # Add user-specific randomization for diversity
                rng = np.random.default_rng(abs(hash(f"{username}_{post_id}")) % (2**32))
                diversity_noise = rng.normal(0, diversity_weight)
                
                final_score = similarity_score + popularity_boost + diversity_noise
                candidate_scores.append((post_id, final_score))
        
        # Sort by score and return top recommendations
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        recommendations = [post_id for post_id, _ in candidate_scores[:top_k]]
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {username}")
        return recommendations
    
    def _get_popular_posts(self, all_posts_df: pd.DataFrame, limit: int = 20) -> List[int]:
        """Get popular posts for cold start scenario."""
        popular_posts = all_posts_df.sort_values(by='view_count', ascending=False)
        return popular_posts['id'].head(limit).tolist()
    
    def get_similar_posts(self, post_id: int, top_k: int = 10) -> List[Tuple[int, float]]:
        
        if self.post_embeddings is None:
            raise ValueError("Post embeddings not built. Call build_embeddings() first.")
        
        try:
            post_idx = self.post_ids.index(post_id)
            post_embedding = self.post_embeddings[post_idx]
            
            # Calculate similarities
            similarities = cosine_similarity([post_embedding], self.post_embeddings)[0]
            
            # Get top similar posts (excluding the post itself)
            similar_posts = []
            for i, sim_score in enumerate(similarities):
                if self.post_ids[i] != post_id:
                    similar_posts.append((self.post_ids[i], sim_score))
            
            similar_posts.sort(key=lambda x: x[1], reverse=True)
            return similar_posts[:top_k]
            
        except ValueError:
            logger.warning(f"Post ID {post_id} not found in embeddings")
            return []


# Convenience functions for backward compatibility
def build_deep_similarity_matrix(all_posts_df: pd.DataFrame) -> DeepContentRecommender:
    recommender = DeepContentRecommender()
    recommender.build_embeddings(all_posts_df)
    return recommender


def get_deep_recommendation(
    username: str, 
    user_profile_df: pd.DataFrame, 
    all_post_df: pd.DataFrame, 
    deep_recommender: DeepContentRecommender
) -> List[int]:
    return deep_recommender.get_recommendations(username, user_profile_df, all_post_df)


def get_popular_posts(all_posts_df: pd.DataFrame, limit: int = 20) -> List[int]:
    """Get popular posts for cold start scenario."""
    popular_posts = all_posts_df.sort_values(by='view_count', ascending=False)
    return popular_posts['id'].head(limit).tolist()
