"""
Unit tests for authentication functionality.

Tests cover:
- Clerk client creation
- Session caching and retrieval
- Session verification
- Cache invalidation
- LRU eviction
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from time import time
from fastapi import HTTPException
from clerk_backend_api.models import Session as ClerkSession

from app.api.auth import (
    get_clerk_client,
    _get_cached_session,
    _cache_session,
    invalidate_session_cache,
    verify_clerk_session,
    _session_cache,
)

# Configure pytest-anyio to only use asyncio backend
pytestmark = pytest.mark.anyio(backends=["asyncio"])


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the session cache before each test."""
    _session_cache.clear()
    yield
    _session_cache.clear()


@pytest.fixture
def mock_clerk_session():
    """Create a mock Clerk session object."""
    session = Mock(spec=ClerkSession)
    session.id = "sess_123456789"
    session.user_id = "user_abc123def456"
    session.status = "active"
    session.client_id = "client_xyz"
    return session


@pytest.fixture
def mock_inactive_session():
    """Create a mock inactive Clerk session."""
    session = Mock(spec=ClerkSession)
    session.id = "sess_inactive"
    session.user_id = "user_inactive"
    session.status = "expired"
    session.client_id = "client_xyz"
    return session


class TestGetClerkClient:
    """Tests for get_clerk_client function."""

    @patch("app.api.auth.Clerk")
    @patch("app.api.auth.settings")
    def test_creates_clerk_client_with_secret_key(self, mock_settings, mock_clerk):
        """Test that Clerk client is created with the correct secret key."""
        mock_settings.CLERK_SECRET_KEY = "test_secret_key"
        
        client = get_clerk_client()
        
        mock_clerk.assert_called_once_with(bearer_auth="test_secret_key")
        assert client == mock_clerk.return_value

    @patch("app.api.auth.Clerk")
    @patch("app.api.auth.settings")
    def test_returns_clerk_instance(self, mock_settings, mock_clerk):
        """Test that function returns a Clerk instance."""
        mock_settings.CLERK_SECRET_KEY = "secret"
        mock_client = Mock()
        mock_clerk.return_value = mock_client
        
        result = get_clerk_client()
        
        assert result == mock_client


class TestSessionCaching:
    """Tests for session caching functions."""

    def test_get_cached_session_returns_none_when_empty(self):
        """Test that retrieving from empty cache returns None."""
        result = _get_cached_session("nonexistent_session")
        assert result is None

    def test_cache_session_stores_session(self, mock_clerk_session):
        """Test that caching stores session with expiry."""
        session_id = "sess_test"
        
        _cache_session(session_id, mock_clerk_session)
        
        assert session_id in _session_cache
        cached_session, expiry = _session_cache[session_id]
        assert cached_session == mock_clerk_session
        assert expiry > time()

    @patch("app.api.auth.settings")
    def test_cache_session_respects_ttl(self, mock_settings, mock_clerk_session):
        """Test that cache respects configured TTL."""
        mock_settings.AUTH_CACHE_TTL = 300
        mock_settings.AUTH_CACHE_MAX_SIZE = 1000
        session_id = "sess_ttl_test"
        current_time = time()
        
        with patch("app.api.auth.time", return_value=current_time):
            _cache_session(session_id, mock_clerk_session)
        
        _, expiry = _session_cache[session_id]
        assert abs(expiry - (current_time + 300)) < 1  # Allow small time drift

    def test_get_cached_session_returns_valid_session(self, mock_clerk_session):
        """Test retrieving a valid cached session."""
        session_id = "sess_valid"
        _cache_session(session_id, mock_clerk_session)
        
        result = _get_cached_session(session_id)
        
        assert result == mock_clerk_session

    def test_get_cached_session_removes_expired_session(self, mock_clerk_session):
        """Test that expired sessions are removed from cache."""
        session_id = "sess_expired"
        # Cache with expired timestamp
        _session_cache[session_id] = (mock_clerk_session, time() - 100)
        
        result = _get_cached_session(session_id)
        
        assert result is None
        assert session_id not in _session_cache

    @patch("app.api.auth.settings")
    def test_cache_implements_lru_eviction(self, mock_settings, mock_clerk_session):
        """Test that cache evicts oldest entry when max size is reached."""
        mock_settings.AUTH_CACHE_MAX_SIZE = 3
        mock_settings.AUTH_CACHE_TTL = 300
        
        # Fill cache to max
        _cache_session("sess_1", mock_clerk_session)
        _cache_session("sess_2", mock_clerk_session)
        _cache_session("sess_3", mock_clerk_session)
        
        assert len(_session_cache) == 3
        assert "sess_1" in _session_cache
        
        # Add one more, should evict sess_1
        _cache_session("sess_4", mock_clerk_session)
        
        assert len(_session_cache) == 3
        assert "sess_1" not in _session_cache
        assert "sess_2" in _session_cache
        assert "sess_3" in _session_cache
        assert "sess_4" in _session_cache

    def test_invalidate_session_cache_removes_session(self, mock_clerk_session):
        """Test that invalidation removes session from cache."""
        session_id = "sess_to_invalidate"
        _cache_session(session_id, mock_clerk_session)
        assert session_id in _session_cache
        
        invalidate_session_cache(session_id)
        
        assert session_id not in _session_cache

    def test_invalidate_session_cache_handles_nonexistent_session(self):
        """Test that invalidating nonexistent session doesn't raise error."""
        try:
            invalidate_session_cache("nonexistent_session")
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")


class TestVerifyClerkSession:
    """Tests for verify_clerk_session function."""

    @pytest.mark.anyio
    async def test_missing_session_id_raises_unauthorized(self):
        """Test that missing session ID raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_clerk_session(session_id=None)
        
        assert exc_info.value.status_code == 401
        assert "X-Session-Id header missing" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_returns_cached_session_when_available(self, mock_clerk_session):
        """Test that cached session is returned without API call."""
        session_id = "sess_cached"
        _cache_session(session_id, mock_clerk_session)
        
        with patch("app.api.auth.get_clerk_client") as mock_get_client:
            result = await verify_clerk_session(session_id=session_id)
        
        # Should not call Clerk API
        mock_get_client.assert_not_called()
        assert result == mock_clerk_session

    @pytest.mark.anyio
    async def test_verifies_session_with_clerk_when_not_cached(self, mock_clerk_session):
        """Test that session is verified with Clerk when not in cache."""
        session_id = "sess_new"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = mock_clerk_session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            result = await verify_clerk_session(session_id=session_id)
        
        mock_sessions.get.assert_called_once_with(session_id=session_id)
        assert result == mock_clerk_session

    @pytest.mark.anyio
    async def test_caches_verified_session(self, mock_clerk_session):
        """Test that successfully verified session is cached."""
        session_id = "sess_to_cache"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = mock_clerk_session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            await verify_clerk_session(session_id=session_id)
        
        # Check that session is now in cache
        cached = _get_cached_session(session_id)
        assert cached == mock_clerk_session

    @pytest.mark.anyio
    async def test_invalid_session_raises_unauthorized(self):
        """Test that invalid session (None) raises 401."""
        session_id = "sess_invalid"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = None  # Invalid session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await verify_clerk_session(session_id=session_id)
        
        assert exc_info.value.status_code == 401
        assert "Invalid session" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_inactive_session_raises_unauthorized(self, mock_inactive_session):
        """Test that inactive session raises 401."""
        session_id = "sess_inactive"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = mock_inactive_session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await verify_clerk_session(session_id=session_id)
        
        assert exc_info.value.status_code == 401
        assert "Session is not active" in exc_info.value.detail
        assert "expired" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_clerk_api_error_raises_unauthorized(self):
        """Test that Clerk API errors are caught and raise 401."""
        session_id = "sess_error"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.side_effect = Exception("Clerk API Error")
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await verify_clerk_session(session_id=session_id)
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in exc_info.value.detail
        assert "Clerk API Error" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_http_exception_is_reraised(self):
        """Test that HTTPException from verification is re-raised as-is."""
        session_id = "sess_http_error"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        
        # Simulate HTTPException being raised
        original_exception = HTTPException(status_code=403, detail="Forbidden")
        mock_sessions.get.side_effect = original_exception
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            with pytest.raises(HTTPException) as exc_info:
                await verify_clerk_session(session_id=session_id)
        
        # Should be the same exception
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Forbidden"

    @pytest.mark.anyio
    async def test_does_not_cache_invalid_session(self):
        """Test that invalid sessions are not cached."""
        session_id = "sess_not_to_cache"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = None
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            try:
                await verify_clerk_session(session_id=session_id)
            except HTTPException:
                pass
        
        # Session should not be cached
        assert session_id not in _session_cache

    @pytest.mark.anyio
    async def test_does_not_cache_inactive_session(self, mock_inactive_session):
        """Test that inactive sessions are not cached."""
        session_id = "sess_inactive_not_cached"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = mock_inactive_session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            try:
                await verify_clerk_session(session_id=session_id)
            except HTTPException:
                pass
        
        # Session should not be cached
        assert session_id not in _session_cache


class TestCacheIntegration:
    """Integration tests for cache behavior."""

    @pytest.mark.anyio
    async def test_multiple_calls_use_cache(self, mock_clerk_session):
        """Test that multiple calls to verify use cache after first call."""
        session_id = "sess_multi"
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = mock_clerk_session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            # First call - should hit API
            result1 = await verify_clerk_session(session_id=session_id)
            # Second call - should use cache
            result2 = await verify_clerk_session(session_id=session_id)
            # Third call - should use cache
            result3 = await verify_clerk_session(session_id=session_id)
        
        # API should only be called once
        assert mock_sessions.get.call_count == 1
        assert result1 == result2 == result3 == mock_clerk_session

    @pytest.mark.anyio
    @patch("app.api.auth.settings")
    async def test_expired_cache_triggers_revalidation(
        self, mock_settings, mock_clerk_session
    ):
        """Test that expired cache entry triggers new API call."""
        mock_settings.AUTH_CACHE_TTL = 1  # 1 second TTL
        mock_settings.AUTH_CACHE_MAX_SIZE = 1000
        session_id = "sess_expire_test"
        
        mock_clerk = MagicMock()
        mock_sessions = Mock()
        mock_sessions.get.return_value = mock_clerk_session
        # Set up context manager behavior
        mock_clerk.__enter__ = Mock(return_value=mock_clerk)
        mock_clerk.__exit__ = Mock(return_value=False)
        mock_clerk.sessions = mock_sessions
        
        with patch("app.api.auth.get_clerk_client", return_value=mock_clerk):
            # First call
            await verify_clerk_session(session_id=session_id)
            
            # Manually expire the cache entry
            _session_cache[session_id] = (mock_clerk_session, time() - 100)
            
            # Second call should trigger new API call
            await verify_clerk_session(session_id=session_id)
        
        # Should have been called twice
        assert mock_sessions.get.call_count == 2

    def test_cache_cleanup_on_expiry_check(self, mock_clerk_session):
        """Test that expired entries are cleaned up when checked."""
        # Add multiple expired entries
        for i in range(5):
            session_id = f"sess_expired_{i}"
            _session_cache[session_id] = (mock_clerk_session, time() - 100)
        
        assert len(_session_cache) == 5
        
        # Check each one - should remove as we go
        for i in range(5):
            result = _get_cached_session(f"sess_expired_{i}")
            assert result is None
        
        assert len(_session_cache) == 0
