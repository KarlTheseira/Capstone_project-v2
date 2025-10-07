"""Rate Limiting Utility Module"""

from functools import wraps
from flask import request, jsonify
from collections import defaultdict
import time

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_rate_limited(self, key, max_requests=100, window_seconds=3600):
        """Check if a key (like IP address) is rate limited"""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        # Check if rate limited
        if len(self.requests[key]) >= max_requests:
            return True
        
        # Add current request
        self.requests[key].append(now)
        return False

# Global rate limiter instance
limiter = RateLimiter()

def rate_limit(max_requests=100, window_seconds=3600):
    """Decorator to apply rate limiting to routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP address as key
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            
            if limiter.is_rate_limited(client_ip, max_requests, window_seconds):
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
