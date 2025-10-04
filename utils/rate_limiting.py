"""
Rate Limiting Service for FlashStudio Payment System
Provides intelligent rate limiting to prevent abuse and ensure system stability
"""
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

class RateLimitStore:
    """
    In-memory rate limit store with Redis-like interface
    Falls back to in-memory storage when Redis is not available
    """
    
    def __init__(self):
        self.store = {}
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection if available"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Rate limiting using Redis backend")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory store: {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[str]:
        """Get value from store"""
        if self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception:
                logger.warning("Redis connection failed, falling back to memory")
                self.redis_client = None
        
        # In-memory fallback
        item = self.store.get(key)
        if item and item['expires'] > time.time():
            return item['value']
        elif item:
            del self.store[key]
        return None
    
    def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in store with TTL"""
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, value)
                return
            except Exception:
                logger.warning("Redis connection failed, falling back to memory")
                self.redis_client = None
        
        # In-memory fallback
        self.store[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
    
    def incr(self, key: str, ttl: int = 3600) -> int:
        """Increment counter with TTL"""
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                result = pipe.execute()
                return result[0]
            except Exception:
                logger.warning("Redis connection failed, falling back to memory")
                self.redis_client = None
        
        # In-memory fallback
        current_time = time.time()
        item = self.store.get(key)
        
        if not item or item['expires'] <= current_time:
            self.store[key] = {
                'value': '1',
                'expires': current_time + ttl
            }
            return 1
        else:
            count = int(item['value']) + 1
            self.store[key] = {
                'value': str(count),
                'expires': item['expires']
            }
            return count
    
    def cleanup_expired(self):
        """Clean up expired in-memory entries"""
        if self.redis_client:
            return  # Redis handles expiration automatically
        
        current_time = time.time()
        expired_keys = [
            key for key, item in self.store.items()
            if item['expires'] <= current_time
        ]
        
        for key in expired_keys:
            del self.store[key]


class PaymentRateLimiter:
    """Advanced rate limiter specifically for payment endpoints"""
    
    def __init__(self):
        self.store = RateLimitStore()
        
        # Rate limit configurations
        self.limits = {
            'payment_intent': {
                'requests': 10,      # 10 requests
                'window': 300,       # per 5 minutes
                'block_duration': 900  # block for 15 minutes
            },
            'payment_confirm': {
                'requests': 5,       # 5 requests  
                'window': 300,       # per 5 minutes
                'block_duration': 1800  # block for 30 minutes
            },
            'webhook': {
                'requests': 100,     # 100 requests
                'window': 60,        # per minute
                'block_duration': 300   # block for 5 minutes
            },
            'analytics': {
                'requests': 50,      # 50 requests
                'window': 300,       # per 5 minutes
                'block_duration': 600   # block for 10 minutes
            }
        }
    
    def _get_client_id(self) -> str:
        """Generate client identifier from request"""
        # Try multiple identification methods
        client_ip = (
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or
            request.headers.get('X-Real-IP') or
            request.remote_addr or
            'unknown'
        )
        
        # Add user session if available
        user_id = getattr(g, 'user_id', None) or request.headers.get('X-User-ID', '')
        
        # Create composite identifier
        identifier_parts = [client_ip]
        if user_id:
            identifier_parts.append(f"user:{user_id}")
        
        # Add user agent hash for additional uniqueness
        user_agent = request.headers.get('User-Agent', '')
        if user_agent:
            ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
            identifier_parts.append(f"ua:{ua_hash}")
        
        return "|".join(identifier_parts)
    
    def _is_whitelisted(self, client_id: str) -> bool:
        """Check if client is whitelisted (for admin, localhost, etc.)"""
        # Whitelist localhost in development
        if '127.0.0.1' in client_id or 'localhost' in client_id:
            return True
        
        # Whitelist admin users (if identifiable)
        if 'admin' in client_id.lower():
            return True
        
        return False
    
    def check_rate_limit(self, endpoint_type: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits
        
        Args:
            endpoint_type: Type of endpoint ('payment_intent', 'payment_confirm', etc.)
            
        Returns:
            Tuple of (is_allowed: bool, limit_info: dict)
        """
        client_id = self._get_client_id()
        
        # Check if whitelisted
        if self._is_whitelisted(client_id):
            return True, {
                'whitelisted': True,
                'client_id': client_id
            }
        
        # Get rate limit config
        config = self.limits.get(endpoint_type, self.limits['payment_intent'])
        
        # Check if currently blocked
        block_key = f"rate_limit:block:{endpoint_type}:{client_id}"
        if self.store.get(block_key):
            return False, {
                'blocked': True,
                'client_id': client_id,
                'endpoint_type': endpoint_type,
                'block_expires_in': config['block_duration']
            }
        
        # Check current request count
        count_key = f"rate_limit:count:{endpoint_type}:{client_id}"
        current_count = self.store.incr(count_key, config['window'])
        
        # Calculate remaining requests and reset time
        remaining = max(0, config['requests'] - current_count)
        reset_time = datetime.utcnow() + timedelta(seconds=config['window'])
        
        # Check if limit exceeded
        if current_count > config['requests']:
            # Block the client
            self.store.set(block_key, "1", config['block_duration'])
            
            logger.warning(f"Rate limit exceeded for {client_id} on {endpoint_type}: {current_count} requests")
            
            return False, {
                'limit_exceeded': True,
                'client_id': client_id,
                'endpoint_type': endpoint_type,
                'requests_made': current_count,
                'limit': config['requests'],
                'window_seconds': config['window'],
                'blocked_until': (datetime.utcnow() + timedelta(seconds=config['block_duration'])).isoformat(),
                'reset_time': reset_time.isoformat()
            }
        
        # Request allowed
        return True, {
            'allowed': True,
            'client_id': client_id,
            'endpoint_type': endpoint_type,
            'requests_made': current_count,
            'limit': config['requests'],
            'remaining': remaining,
            'reset_time': reset_time.isoformat(),
            'window_seconds': config['window']
        }
    
    def get_rate_limit_headers(self, limit_info: Dict[str, Any]) -> Dict[str, str]:
        """Generate rate limit headers for HTTP response"""
        headers = {}
        
        if limit_info.get('allowed') or limit_info.get('limit_exceeded'):
            headers.update({
                'X-RateLimit-Limit': str(limit_info.get('limit', 0)),
                'X-RateLimit-Remaining': str(limit_info.get('remaining', 0)),
                'X-RateLimit-Reset': limit_info.get('reset_time', ''),
                'X-RateLimit-Window': str(limit_info.get('window_seconds', 0))
            })
        
        if limit_info.get('limit_exceeded'):
            headers['Retry-After'] = str(limit_info.get('window_seconds', 300))
        
        return headers
    
    def cleanup(self):
        """Clean up expired entries"""
        self.store.cleanup_expired()


# Global rate limiter instance
rate_limiter = PaymentRateLimiter()


def rate_limit(endpoint_type: str):
    """
    Decorator for applying rate limiting to endpoints
    
    Args:
        endpoint_type: Type of endpoint for rate limiting rules
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check rate limit
            is_allowed, limit_info = rate_limiter.check_rate_limit(endpoint_type)
            
            # Generate headers
            headers = rate_limiter.get_rate_limit_headers(limit_info)
            
            if not is_allowed:
                # Rate limit exceeded
                error_response = {
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'limit_info': {
                        'requests_made': limit_info.get('requests_made'),
                        'limit': limit_info.get('limit'),
                        'window_seconds': limit_info.get('window_seconds'),
                        'reset_time': limit_info.get('reset_time'),
                        'blocked_until': limit_info.get('blocked_until')
                    }
                }
                
                # Log rate limit violation
                logger.warning(f"Rate limit exceeded: {limit_info}")
                
                response = jsonify(error_response)
                response.status_code = 429
                
                # Add headers
                for header, value in headers.items():
                    response.headers[header] = value
                
                return response
            
            # Execute the original function
            response = f(*args, **kwargs)
            
            # Add rate limit headers to successful response
            if hasattr(response, 'headers'):
                for header, value in headers.items():
                    response.headers[header] = value
            
            return response
        
        return decorated_function
    return decorator


class RateLimitMonitor:
    """Monitor and report on rate limiting activity"""
    
    def __init__(self):
        self.limiter = rate_limiter
    
    def get_rate_limit_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        try:
            stats = {
                'monitoring_period_hours': hours,
                'endpoints': {},
                'total_requests': 0,
                'total_blocked': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # This would require storing rate limit events
            # For now, return basic structure
            for endpoint_type in self.limiter.limits.keys():
                stats['endpoints'][endpoint_type] = {
                    'limit': self.limiter.limits[endpoint_type]['requests'],
                    'window_seconds': self.limiter.limits[endpoint_type]['window'],
                    'block_duration': self.limiter.limits[endpoint_type]['block_duration'],
                    'requests_allowed': 0,  # Would track from events
                    'requests_blocked': 0,  # Would track from events
                    'unique_clients': 0     # Would track from events
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error generating rate limit stats: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check rate limiting system health"""
        health = {
            'rate_limiter_active': True,
            'store_backend': 'redis' if self.limiter.store.redis_client else 'memory',
            'configured_endpoints': list(self.limiter.limits.keys()),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test rate limiter functionality
        try:
            test_allowed, test_info = self.limiter.check_rate_limit('payment_intent')
            health['functionality_test'] = 'passed'
        except Exception as e:
            health['functionality_test'] = f'failed: {e}'
        
        return health


# Global monitor instance
rate_limit_monitor = RateLimitMonitor()


def init_rate_limiting(app):
    """Initialize rate limiting for Flask app"""
    logger.info("Initializing payment rate limiting system")
    
    # Add cleanup task (run periodically)
    @app.before_request
    def cleanup_rate_limits():
        # Clean up expired entries occasionally (1% of requests)
        if time.time() % 100 == 0:
            rate_limiter.cleanup()
    
    # Add rate limit info to context
    @app.before_request  
    def add_rate_limit_context():
        g.rate_limiter = rate_limiter
        g.rate_limit_monitor = rate_limit_monitor
    
    logger.info("Rate limiting system initialized successfully")