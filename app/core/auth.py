from fastapi import HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from clerk_backend_api import Clerk
from clerk_backend_api.models import Session as ClerkSession
from app.core.config import Settings

settings = Settings()

session_id_header = APIKeyHeader(name="X-Session-Id", auto_error=False)


def get_clerk_client() -> Clerk:
    """
    Create and return a Clerk client instance.
    
    Returns:
        Clerk: Configured Clerk client.
    """
    return Clerk(bearer_auth=settings.CLERK_SECRET_KEY)


async def verify_clerk_session(session_id: str | None = Depends(session_id_header)) -> ClerkSession:
    """
    Verify Clerk session token and return session information.
    
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
            
            return session
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )