from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from app.core.logging import get_logger
from app.services.message import MessageService
from app.services.chat import ChatService
from app.api.depends import SessionDep, CurrentUser
from app.models import (
    MessageCreate, 
    MessageUpdate, 
    MessagePublic, 
    MessageResponse,
    MessageWithAutoChatRequest,
    MessageWithAutoChatResponse,
    MessageFeedbackRequest,
    ConversationSummaryResponse,
    MessageBulkOperationRequest,
    BulkOperationResponse
)


router = APIRouter()
logger = get_logger(__name__)


# ==========================================
# POST routes
# ==========================================

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MessagePublic)
async def create_message(
    message_data: MessageCreate,
    session: SessionDep,
    user: CurrentUser
):
    """
    Create a new message in an existing chat.
    
    Args:
        message_data: Message creation data (chat_id, model_id, type, content, tokens)
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Created message with model details
        
    Raises:
        HTTPException: If chat doesn't exist or user doesn't have access, or if model is invalid
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(message_data.chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {message_data.chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    try:
        message = service.create_message(message_data, user_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create message"
            )
        logger.info(f"Created message in chat {message_data.chat_id} for user {user_id}")
        return message
    except ValueError as e:
        logger.error(f"Validation error creating message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/with-chat", status_code=status.HTTP_201_CREATED, response_model=MessageWithAutoChatResponse)
async def create_message_with_auto_chat(
    request: MessageWithAutoChatRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Create a new message and automatically create a chat if needed.
    This is useful for starting a new conversation.
    
    Args:
        request: Message creation request with optional chat title
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Created message with chat_id
        
    Raises:
        HTTPException: If model is invalid or disabled
    """
    service = MessageService(session)
    user_id = user.user_id
    
    try:
        message, chat_id = service.create_message_with_auto_chat(
            user_id=user_id,
            model_id=request.model_id,
            content=request.content,
            message_type=request.message_type,
            tokens=request.tokens,
            chat_title=request.chat_title
        )
        logger.info(f"Created message with auto chat for user {user_id}, chat_id={chat_id}")
        return MessageWithAutoChatResponse(message=message, chat_id=chat_id)
    except ValueError as e:
        logger.error(f"Validation error creating message with auto chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/bulk/delete", response_model=BulkOperationResponse)
async def bulk_delete_messages(
    request: MessageBulkOperationRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Soft delete multiple messages at once.
    
    Args:
        request: Bulk operation request containing list of message IDs
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Summary of successful and failed deletions
        
    Note: Only messages in chats owned by the user will be deleted
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Batch fetch all messages by IDs
    messages = service.get_messages_by_ids(request.message_ids)
    # Extract unique chat IDs from messages
    chat_ids = list({msg.chat_id for msg in messages})
    # Batch fetch all chats owned by the user
    chats = chat_service.get_chats_by_ids_and_user(chat_ids, user_id)
    owned_chat_ids = {chat.id for chat in chats}
    # Filter messages to those in chats owned by the user
    accessible_ids = [msg.id for msg in messages if msg.chat_id in owned_chat_ids]
    
    result = service.bulk_delete_messages(accessible_ids)
    logger.info(
        f"Bulk deleted messages for user {user_id}: "
        f"successful={result['successful']}, failed={result['failed']}"
    )
    return BulkOperationResponse(**result)


@router.post("/bulk/delete/permanent", response_model=BulkOperationResponse)
async def bulk_permanently_delete_messages(
    request: MessageBulkOperationRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Permanently delete multiple messages at once (cannot be restored).
    
    Args:
        request: Bulk operation request containing list of message IDs
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Summary of successful and failed deletions
        
    Note: Only messages in chats owned by the user will be deleted
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Filter message IDs to only those the user has access to
    accessible_ids = []
    for message_id in request.message_ids:
        message = service.get_message_by_id(message_id)
        if message:
            chat = chat_service.get_chat_by_id(message.chat_id, user_id)
            if chat:
                accessible_ids.append(message_id)
    
    result = service.bulk_permanently_delete_messages(accessible_ids)
    logger.info(
        f"Bulk permanently deleted messages for user {user_id}: "
        f"successful={result['successful']}, failed={result['failed']}"
    )
    return BulkOperationResponse(**result)


# ==========================================
# GET routes - most specific first
# ==========================================

@router.get("/chat/{chat_id}/active", response_model=list[MessagePublic])
async def get_active_messages(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get all active (non-deleted) messages for a chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        
    Returns:
        List of active messages
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    messages = service.get_active_messages(chat_id, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(messages)} active messages for chat {chat_id}")
    return messages


@router.get("/chat/{chat_id}/type/{message_type}", response_model=list[MessagePublic])
async def get_messages_by_type(
    chat_id: UUID,
    message_type: str,
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get messages by type for a specific chat.
    
    Args:
        chat_id: Chat UUID
        message_type: Message type (user, ai, system)
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        
    Returns:
        List of messages of the specified type
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    messages = service.get_messages_by_type(chat_id, message_type, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(messages)} messages of type '{message_type}' for chat {chat_id}")
    return messages


@router.get("/chat/{chat_id}/user", response_model=list[MessagePublic])
async def get_user_messages(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get all user messages for a chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        
    Returns:
        List of user messages
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    messages = service.get_user_messages(chat_id, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(messages)} user messages for chat {chat_id}")
    return messages


@router.get("/chat/{chat_id}/ai", response_model=list[MessagePublic])
async def get_ai_messages(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get all AI messages for a chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        
    Returns:
        List of AI messages
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    messages = service.get_ai_messages(chat_id, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(messages)} AI messages for chat {chat_id}")
    return messages


@router.get("/chat/{chat_id}/latest", response_model=MessagePublic)
async def get_latest_message(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Get the latest message in a chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Latest message
        
    Raises:
        HTTPException: If chat not found, user doesn't have access, or no messages exist
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    message = service.get_latest_message(chat_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No messages found in this chat"
        )
    
    logger.info(f"Retrieved latest message for chat {chat_id}")
    return message


@router.get("/chat/{chat_id}/count", response_model=dict)
async def count_chat_messages(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser,
    include_deleted: bool = Query(False, description="Include soft-deleted messages in count")
):
    """
    Count total messages in a chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        include_deleted: If True, include soft-deleted messages (default: False)
        
    Returns:
        Dictionary with message count
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    count = service.count_chat_messages(chat_id, include_deleted=include_deleted)
    logger.info(f"Message count for chat {chat_id}: {count}")
    return {"count": count}


@router.get("/chat/{chat_id}/summary", response_model=ConversationSummaryResponse)
async def get_conversation_summary(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Get a summary of the conversation including counts, tokens, and cost.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Conversation statistics
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    summary = service.get_conversation_summary(chat_id)
    logger.info(f"Retrieved conversation summary for chat {chat_id}")
    return ConversationSummaryResponse(**summary)


@router.get("/chat/{chat_id}/feedback", response_model=list[MessagePublic])
async def get_messages_with_feedback(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser,
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type (positive/negative)")
):
    """
    Get messages that have feedback, optionally filtered by feedback type.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        feedback_type: Optional filter for 'positive' or 'negative'
        
    Returns:
        List of messages with feedback
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    messages = service.get_messages_with_feedback(chat_id, feedback_type=feedback_type)
    logger.info(f"Retrieved {len(messages)} messages with feedback for chat {chat_id}")
    return messages


@router.get("/chat/{chat_id}", response_model=list[MessagePublic])
async def get_chat_messages(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    include_deleted: bool = Query(False, description="Include soft-deleted messages")
):
    """
    Get all messages for a chat with pagination.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        include_deleted: If True, include soft-deleted messages (default: False)
        
    Returns:
        List of messages ordered by creation time
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    messages = service.get_chat_messages(
        chat_id,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted
    )
    logger.info(f"Retrieved {len(messages)} messages for chat {chat_id} (skip={skip}, limit={limit})")
    return messages


@router.get("/{message_id}/exists", response_model=dict)
async def check_message_exists(
    message_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Check if a message exists and user has access to it.
    
    Args:
        message_id: Message UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Dictionary indicating whether the message exists and is accessible
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    message = service.get_message_by_id(message_id)
    if not message:
        logger.info(f"Message {message_id} does not exist")
        return {"exists": False}
    
    # Check if user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    exists = chat is not None
    
    logger.info(f"Checked existence of message {message_id} for user {user_id}: {exists}")
    return {"exists": exists}


@router.get("/{message_id}", response_model=MessagePublic)
async def get_message_by_id(
    message_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Get a specific message by ID.
    
    Args:
        message_id: Message UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Message with the specified ID
        
    Raises:
        HTTPException: If message not found or user doesn't have access to the chat
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    message = service.get_message_by_id(message_id)
    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    if not chat:
        logger.warning(f"Access denied to message {message_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have access"
        )
    
    logger.info(f"Retrieved message {message_id} for user {user_id}")
    return message


# ==========================================
# PUT routes
# ==========================================

@router.put("/{message_id}", response_model=MessagePublic)
async def update_message(
    message_id: UUID,
    message_data: MessageUpdate,
    session: SessionDep,
    user: CurrentUser
):
    """
    Update a message.
    
    Args:
        message_id: Message UUID
        message_data: Message update data
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Updated message
        
    Raises:
        HTTPException: If message not found, user doesn't have access, or validation fails
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Get message to verify access
    message = service.get_message_by_id(message_id)
    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    if not chat:
        logger.warning(f"Access denied to update message {message_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have access"
        )
    
    try:
        updated_message = service.update_message(message_id, message_data)
        if not updated_message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update message"
            )
        logger.info(f"Updated message {message_id} for user {user_id}")
        return updated_message
    except ValueError as e:
        logger.error(f"Validation error updating message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==========================================
# PATCH routes - specific before generic
# ==========================================

@router.patch("/{message_id}/content", response_model=MessagePublic)
async def update_message_content(
    message_id: UUID,
    content: str,
    session: SessionDep,
    user: CurrentUser
):
    """
    Update only the content of a message.
    
    Args:
        message_id: Message UUID
        content: New content
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Updated message
        
    Raises:
        HTTPException: If message not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Get message to verify access
    message = service.get_message_by_id(message_id)
    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    if not chat:
        logger.warning(f"Access denied to update message {message_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have access"
        )
    
    updated_message = service.update_message_content(message_id, content)
    if not updated_message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update message content"
        )
    
    logger.info(f"Updated content for message {message_id} for user {user_id}")
    return updated_message


@router.patch("/{message_id}/feedback", response_model=MessagePublic)
async def update_message_feedback(
    message_id: UUID,
    request: MessageFeedbackRequest,
    session: SessionDep,
    user: CurrentUser
):
    """
    Update message feedback (positive/negative).
    
    Args:
        message_id: Message UUID
        request: Feedback update request
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Updated message
        
    Raises:
        HTTPException: If message not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Get message to verify access
    message = service.get_message_by_id(message_id)
    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    if not chat:
        logger.warning(f"Access denied to update message {message_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have access"
        )
    
    updated_message = service.update_message_feedback(message_id, request.feedback)
    if not updated_message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update message feedback"
        )
    
    logger.info(f"Updated feedback for message {message_id} for user {user_id}")
    return updated_message


# ==========================================
# DELETE routes - specific before generic
# ==========================================

@router.delete("/chat/{chat_id}/all", status_code=status.HTTP_200_OK, response_model=dict)
async def delete_all_chat_messages(
    chat_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Soft delete all messages in a chat.
    
    Args:
        chat_id: Chat UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Count of deleted messages
        
    Raises:
        HTTPException: If chat not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Verify chat exists and user has access
    chat = chat_service.get_chat_by_id(chat_id, user_id)
    if not chat:
        logger.warning(f"Chat not found or access denied: {chat_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or you don't have access"
        )
    
    deleted_count = service.delete_chat_messages(chat_id)
    logger.info(f"Deleted {deleted_count} messages from chat {chat_id} for user {user_id}")
    return {"deleted_count": deleted_count}


@router.delete("/{message_id}/permanent", status_code=status.HTTP_200_OK, response_model=MessageResponse)
async def permanently_delete_message(
    message_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Permanently delete a message (cannot be restored).
    
    Args:
        message_id: Message UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If message not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Get message to verify access
    message = service.get_message_by_id(message_id)
    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    if not chat:
        logger.warning(f"Access denied to permanently delete message {message_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have access"
        )
    
    deleted = service.permanently_delete_message(message_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to permanently delete message"
        )
    
    logger.info(f"Permanently deleted message {message_id} for user {user_id}")
    return MessageResponse(message="Message permanently deleted")


@router.delete("/{message_id}", status_code=status.HTTP_200_OK, response_model=MessageResponse)
async def delete_message(
    message_id: UUID,
    session: SessionDep,
    user: CurrentUser
):
    """
    Soft delete a message (mark as deleted, can be restored).
    
    Args:
        message_id: Message UUID
        session: Database session dependency
        user: Authenticated user from Clerk session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If message not found or user doesn't have access
    """
    service = MessageService(session)
    chat_service = ChatService(session)
    user_id = user.user_id
    
    # Get message to verify access
    message = service.get_message_by_id(message_id)
    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user has access to the chat
    chat = chat_service.get_chat_by_id(message.chat_id, user_id)
    if not chat:
        logger.warning(f"Access denied to delete message {message_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have access"
        )
    
    deleted = service.delete_message(message_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete message"
        )
    
    logger.info(f"Soft deleted message {message_id} for user {user_id}")
    return MessageResponse(message="Message deleted successfully")
