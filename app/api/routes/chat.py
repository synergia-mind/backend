from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.chat import ChatService
from app.api.depends import SessionDep, CurrentUser
from app.models import ChatCreate, ChatUpdate, ChatPublic, MessageResponse


router = APIRouter()
logger = get_logger(__name__)


class BulkOperationRequest(BaseModel):
    """Request model for bulk operations on chats."""
    chat_ids: list[UUID]


class BulkOperationResponse(BaseModel):
    """Response model for bulk operations."""
    successful: int
    failed: int
    total: int


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ChatPublic)
async def create_chat(
    chat_data: ChatCreate,
    session: SessionDep,
    user: CurrentUser
):
    """
    Create a new chat for the authenticated user.
    
    Args:
        chat_data: Chat creation data (title, summary)
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Created chat
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chat = service.create_chat(user_id, chat_data)
    logger.info(f"Created chat for user {user_id}: {chat.title} (ID: {chat.id})")
    return chat


@router.get("/", response_model=list[ChatPublic])
async def get_user_chats(
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    include_deleted: bool = Query(False, description="Include soft-deleted chats")
):
    """
    Get all chats for the authenticated user with pagination.
    
    Args:
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        include_deleted: If True, include soft-deleted chats (default: False)
        
    Returns:
        List of chats ordered by most recent first
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chats = service.get_all_user_chats(
        user_id,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted
    )
    logger.info(f"Retrieved {len(chats)} chats for user {user_id} (skip={skip}, limit={limit})")
    return chats


@router.get("/active", response_model=list[ChatPublic])
async def get_active_chats(
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get all active (non-deleted) chats for the authenticated user.
    
    Args:
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        
    Returns:
        List of active chats
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chats = service.get_active_chats(user_id, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(chats)} active chats for user {user_id}")
    return chats


@router.get("/deleted", response_model=list[ChatPublic])
async def get_deleted_chats(
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get all soft-deleted chats for the authenticated user.
    
    Args:
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        
    Returns:
        List of deleted chats
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chats = service.get_deleted_chats(user_id, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(chats)} deleted chats for user {user_id}")
    return chats


@router.get("/count", response_model=dict)
async def count_user_chats(
    session: SessionDep,
    user: CurrentUser,
    include_deleted: bool = Query(False, description="Include soft-deleted chats in count")
):
    """
    Count total chats for the authenticated user.
    
    Args:
        session: Database session dependency
        user: Authenticated user from Clerk session
        include_deleted: If True, include soft-deleted chats (default: False)
        
    Returns:
        Dictionary with counts: total, active, deleted
    """
    service = ChatService(session)
    user_id = user.user_id
    
    total = service.count_user_chats(user_id, include_deleted=True)
    active = service.count_active_chats(user_id)
    deleted = service.count_deleted_chats(user_id)
    
    logger.info(f"Chat count for user {user_id}: total={total}, active={active}, deleted={deleted}")
    return {
        "total": total,
        "active": active,
        "deleted": deleted
    }


@router.get("/{chat_id}", response_model=ChatPublic)
async def get_chat_by_id(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Get a specific chat by ID for the authenticated user.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Chat with the specified ID
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chat = service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Retrieved chat {chat_id} for user {user_id}")
    return chat


@router.put("/{chat_id}", response_model=ChatPublic)
async def update_chat(
    chat_id: UUID,
    chat_data: ChatUpdate,
    session: SessionDep,
    user: CurrentUser
):
    """
    Update a chat for the authenticated user.
    
    Args:
        chat_id: Chat UUID
        chat_data: Chat update data
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Updated chat
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chat = service.update_chat(chat_id, user_id, chat_data)
    if not chat:
        logger.warning(f"Chat not found for update: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Updated chat {chat_id} for user {user_id}")
    return chat


@router.patch("/{chat_id}/title", response_model=ChatPublic)
async def update_chat_title(
    chat_id: UUID,
    title: str,
    session: SessionDep,
    user: CurrentUser
):
    """
    Update only the title of a chat.
    
    Args:
        chat_id: Chat UUID
        title: New title
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Updated chat
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chat = service.update_chat_title(chat_id, user_id, title)
    if not chat:
        logger.warning(f"Chat not found for title update: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Updated title for chat {chat_id} for user {user_id}")
    return chat


@router.patch("/{chat_id}/summary", response_model=ChatPublic)
async def update_chat_summary(
    chat_id: UUID,
    summary: str,
    session: SessionDep,
    user: CurrentUser
):
    """
    Update only the summary of a chat.
    
    Args:
        chat_id: Chat UUID
        summary: New summary
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Updated chat
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chat = service.update_chat_summary(chat_id, user_id, summary)
    if not chat:
        logger.warning(f"Chat not found for summary update: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Updated summary for chat {chat_id} for user {user_id}")
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_200_OK, response_model=MessageResponse)
async def delete_chat(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Soft delete a chat (mark as deleted, can be restored).
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    deleted = service.delete_chat(chat_id, user_id)
    if not deleted:
        logger.warning(f"Chat not found for deletion: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Soft deleted chat {chat_id} for user {user_id}")
    return MessageResponse(message="Chat deleted successfully")


@router.delete("/{chat_id}/permanent", status_code=status.HTTP_200_OK, response_model=MessageResponse)
async def permanently_delete_chat(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Permanently delete a chat (cannot be restored).
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    deleted = service.permanently_delete_chat(chat_id, user_id)
    if not deleted:
        logger.warning(f"Chat not found for permanent deletion: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Permanently deleted chat {chat_id} for user {user_id}")
    return MessageResponse(message="Chat permanently deleted")


@router.post("/{chat_id}/restore", response_model=ChatPublic)
async def restore_chat(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Restore a soft-deleted chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Restored chat
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = ChatService(session)
    user_id = user.user_id
    
    chat = service.restore_chat(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found for restoration: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    logger.info(f"Restored chat {chat_id} for user {user_id}")
    return chat


@router.post("/bulk/delete", response_model=BulkOperationResponse)
async def bulk_delete_chats(
    request: BulkOperationRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Soft delete multiple chats at once.
    
    Args:
        request: Bulk operation request containing list of chat IDs
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Summary of successful and failed deletions
    """
    service = ChatService(session)
    user_id = user.user_id
    
    result = service.bulk_delete_chats(request.chat_ids, user_id)
    logger.info(
        f"Bulk deleted chats for user {user_id}: "
        f"successful={result['successful']}, failed={result['failed']}"
    )
    return BulkOperationResponse(**result)


@router.post("/bulk/restore", response_model=BulkOperationResponse)
async def bulk_restore_chats(
    request: BulkOperationRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Restore multiple soft-deleted chats at once.
    
    Args:
        request: Bulk operation request containing list of chat IDs
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Summary of successful and failed restorations
    """
    service = ChatService(session)
    user_id = user.user_id
    
    result = service.bulk_restore_chats(request.chat_ids, user_id)
    logger.info(
        f"Bulk restored chats for user {user_id}: "
        f"successful={result['successful']}, failed={result['failed']}"
    )
    return BulkOperationResponse(**result)


@router.post("/bulk/delete/permanent", response_model=BulkOperationResponse)
async def bulk_permanently_delete_chats(
    request: BulkOperationRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Permanently delete multiple chats at once (cannot be restored).
    
    Args:
        request: Bulk operation request containing list of chat IDs
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Summary of successful and failed deletions
    """
    service = ChatService(session)
    user_id = user.user_id
    
    result = service.bulk_permanently_delete_chats(request.chat_ids, user_id)
    logger.info(
        f"Bulk permanently deleted chats for user {user_id}: "
        f"successful={result['successful']}, failed={result['failed']}"
    )
    return BulkOperationResponse(**result)


@router.get("/{chat_id}/exists", response_model=dict)
async def check_chat_exists(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Check if a chat exists for the authenticated user.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Dictionary indicating whether the chat exists
    """
    service = ChatService(session)
    user_id = user.user_id
    
    exists = service.chat_exists(chat_id, user_id)
    logger.info(f"Checked existence of chat {chat_id} for user {user_id}: {exists}")
    return {"exists": exists}
