from typing import Annotated

from sqlmodel import Session
from fastapi import Depends
from clerk_backend_api.models import Session as ClerkSession

from app.core.db import get_session
from app.api.auth import verify_clerk_session

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[ClerkSession, Depends(verify_clerk_session)]