from fastapi import HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from clerk_backend_api import Clerk
from clerk_backend_api.models import Session as ClerkSession
from time import time
from typing import Dict, Tuple
from app.core import settings

session_id_header = APIKeyHeader(name="X-Session-Id", auto_error=False)

# Cache structure: {session_id: (session_object, expiry_timestamp)}
_session_cache: Dict[str, Tuple[ClerkSession, float]] = {}


def get_clerk_client() -> Clerk:
    """
    Create and return a Clerk client instance.
    
    Returns:
        Clerk: Configured Clerk client.
    """
    return Clerk(bearer_auth=settings.CLERK_SECRET_KEY)


def _get_cached_session(session_id: str) -> ClerkSession | None:
    """
    Retrieve a session from cache if valid and not expired.
    
    Args:
        session_id: The session ID to look up.
        
    Returns:
        ClerkSession if cached and valid, None otherwise.
    """
    if session_id in _session_cache:
        session, expiry = _session_cache[session_id]
        if time() < expiry:
            return session
        else:
            # Remove expired entry
            del _session_cache[session_id]
    return None


def _cache_session(session_id: str, session: ClerkSession) -> None:
    """
    Store a session in the cache with TTL.
    
    Implements LRU eviction when cache exceeds max size.
    
    Args:
        session_id: The session ID.
        session: The session object to cache.
    """
    # Implement LRU eviction if cache is full
    if len(_session_cache) >= settings.AUTH_CACHE_MAX_SIZE:
        # Remove oldest entry (first item in dict, as Python 3.7+ maintains insertion order)
        oldest_key = next(iter(_session_cache))
        del _session_cache[oldest_key]
    
    expiry = time() + settings.AUTH_CACHE_TTL
    _session_cache[session_id] = (session, expiry)


def invalidate_session_cache(session_id: str) -> None:
    """
    Manually invalidate a cached session.
    
    Args:
        session_id: The session ID to invalidate.
    """
    _session_cache.pop(session_id, None)


async def verify_clerk_session(session_id: str | None = Depends(session_id_header)) -> ClerkSession:
    """
    Verify Clerk session token and return session information.
    
    Uses LRU cache with TTL to improve performance by avoiding redundant
    API calls to Clerk for recently verified sessions.
    
    Args:
        session_id: Session ID from X-Session-Id header.
        
    Returns:
        ClerkSession: Verified Clerk session object.
        
    Raises:
        HTTPException: If authentication fails.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Session-Id header missing",
        )
    
    # Check cache first
    cached_session = _get_cached_session(session_id)
    if cached_session:
        return cached_session
    
    # Verify session with Clerk
    try:
        with get_clerk_client() as clerk:
            session = clerk.sessions.get(session_id=session_id)
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session",
                )
            
            # Check if session is active
            if session.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Session is not active: {session.status}",
                )
            
            # Cache the valid session
            _cache_session(session_id, session)
            
            return session
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )