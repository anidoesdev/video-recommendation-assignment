# System Overview

This service provides a **deep learning-based** video recommendation API built with FastAPI and BERT embeddings.

## Algorithm
- **Deep Learning**: Uses pre-trained BERT models (Sentence Transformers) for semantic content understanding
- **Content Processing**: Combines title, tags, category name, and topic name into rich text representations
- **User Profiling**: Creates weighted user embeddings from interaction history (view=1.0, like=4.0, inspire=5.0, plus ratings)
- **Recommendation**: Calculates cosine similarity between user profile and all post embeddings
- **Diversity**: Adds popularity boost and user-specific randomization for better recommendations
- **Cold Start**: Returns popular posts by view_count for new users

## Deep Learning Model
- **Model**: `all-MiniLM-L6-v2` (lightweight, fast, good quality)
- **Embeddings**: 384-dimensional semantic vectors
- **Device**: Auto-detects CUDA/MPS/CPU for optimal performance
- **Batch Processing**: Efficient embedding generation with progress tracking

## External Data
- Socialverse API (`API_BASE_URL`) with `Flic-Token` header
- Endpoints used:
  - `/posts/summary/get` for all posts (paged at 1000)
  - `/posts/view|like|inspire|rating?username={username}` for user interactions

## API Endpoints
- `GET /health`
  - Returns readiness, posts cached, model status, and model name
- `GET /feed`
  - Query params: `username` (required), `project_code` (optional), `page` (default 1), `page_size` (default 20)
  - Returns paginated list of personalized recommendations
- `GET /similar/{post_id}`
  - Query params: `top_k` (default 10)
  - Returns posts similar to a given post using BERT embeddings

## Caching & Performance
- Posts and embeddings are loaded and cached in memory at startup
- BERT model is loaded once and reused for all requests
- Embeddings are pre-computed for fast similarity calculations
- For production, consider TTL refresh and background updates

## Error Handling
- External fetches use timeouts and exponential backoff retries
- If data not loaded, endpoints return HTTP 503
- Graceful fallback to popular posts for cold start scenarios

## Configuration
- `.env` variables:
  - `FLIC_TOKEN`
  - `API_BASE_URL`
  - `DATABASE_URL` (used by Alembic via env override)

## Deep Learning Benefits
- **Semantic Understanding**: Captures meaning beyond keyword matching
- **Context Awareness**: Understands relationships between concepts
- **Multilingual Support**: Works across different languages
- **Scalability**: Efficient embedding-based similarity calculations

## Future Enhancements
- Add diversity re-ranking (MMR/topic coverage)
- Apply recency decay to interaction weights
- Background refresh of post cache with TTL
- Fine-tune BERT model on domain-specific data
- Add collaborative filtering hybridization
- Unit tests and CI