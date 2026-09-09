import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request
from app.core.config import settings
from app.core.exceptions import RateLimitException

# In-memory sliding window fallback
_rate_limit_cache: Dict[str, List[float]] = defaultdict(list)


async def check_rate_limit(request: Request, key_prefix: str = "analyze", limit: int = None):
    max_requests = limit or settings.ANALYZE_RATE_LIMIT_PER_MINUTE
    client_ip = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{client_ip}"
    
    current_time = time.time()
    window_start = current_time - 60.0  # 1 minute window
    
    # Prune expired timestamps
    _rate_limit_cache[key] = [t for t in _rate_limit_cache[key] if t > window_start]
    
    if len(_rate_limit_cache[key]) >= max_requests:
        raise RateLimitException(
            f"Rate limit of {max_requests} requests per minute exceeded for AI analysis. Please wait before submitting more."
        )
        
    _rate_limit_cache[key].append(current_time)
