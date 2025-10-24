from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.repositories.chat import ChatRepository
from app.models import Chat, ChatCreate, ChatUpdate, ChatPublic


class ChatService:
    """Service layer for Chat business logic."""
    
    def __init__(self, session: Session):
        self.repository = ChatRepository(session)
    
    def create_chat(self, user_id: str, chat_data: ChatCreate) -> ChatPublic:
        """
        Create a new chat for a user.
        
        Args:
            user_id: User ID string (from authenticated user)
            chat_data: Chat creation data
            
        Returns:
            Created chat as ChatPublic
        """
        chat = self.repository.create(user_id, chat_data)
        return ChatPublic.model_validate(chat)
    
    def get_or_create_chat(
        self,
        user_id: str,
        chat_id: Optional[UUID] = None,
        auto_title: Optional[str] = None
    ) -> ChatPublic:
        """
        Get an existing chat or create a new one if chat_id is None.
        Useful for message creation flows where a chat may or may not exist.
        
        Args:
            user_id: User ID string
            chat_id: Optional chat UUID. If None, creates a new chat
            auto_title: Title for auto-created chat (default: "New Chat")
            
        Returns:
            ChatPublic instance (existing or newly created)
            
        Raises:
            ValueError: If chat_id is provided but doesn't exist or user doesn't own it
        """
        if chat_id is not None:
            # Try to get existing chat
            chat = self.repository.get_by_id(chat_id, user_id)
            if not chat:
                raise ValueError(f"Chat with ID '{chat_id}' does not exist or you don't have access")
            return ChatPublic.model_validate(chat)
        
        # Create new chat
        title = auto_title or "New Chat"
        chat_data = ChatCreate(title=title)
        return self.create_chat(user_id, chat_data)
    
    def get_chat_by_id(self, chat_id: UUID, user_id: str) -> Optional[ChatPublic]:
        """
        Get a chat by ID for a specific user.
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            
        Returns:
            ChatPublic instance or None if not found or user doesn't own it
        """
        chat = self.repository.get_by_id(chat_id, user_id)
        if not chat:
            return None
        return ChatPublic.model_validate(chat)
    
    def get_all_user_chats(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> list[ChatPublic]:
        """
        Get all chats for a user with pagination.
        
        Args:
            user_id: User ID string
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: If True, include soft-deleted chats
            
        Returns:
            List of ChatPublic instances ordered by most recent first
        """
        chats = self.repository.get_all_by_user(
            user_id,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted
        )
        return [ChatPublic.model_validate(chat) for chat in chats]
    
    def get_active_chats(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[ChatPublic]:
        """
        Get all active (non-deleted) chats for a user.
        
        Args:
            user_id: User ID string
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active ChatPublic instances
        """
        return self.get_all_user_chats(
            user_id,
            skip=skip,
            limit=limit,
            include_deleted=False
        )
    
    def update_chat(
        self,
        chat_id: UUID,
        user_id: str,
        chat_data: ChatUpdate
    ) -> Optional[ChatPublic]:
        """
        Update a chat.
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            chat_data: Chat update data
            
        Returns:
            Updated ChatPublic instance or None if not found or user doesn't own it
        """
        chat = self.repository.update(chat_id, user_id, chat_data)
        if not chat:
            return None
        return ChatPublic.model_validate(chat)
    
    def delete_chat(self, chat_id: UUID, user_id: str) -> bool:
        """
        Soft delete a chat (mark as deleted, can be restored).
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            
        Returns:
            True if deleted, False if not found or user doesn't own it
        """
        return self.repository.soft_delete(chat_id, user_id)
    
    def permanently_delete_chat(self, chat_id: UUID, user_id: str) -> bool:
        """
        Permanently delete a chat (cannot be restored).
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            
        Returns:
            True if deleted, False if not found or user doesn't own it
        """
        return self.repository.hard_delete(chat_id, user_id)
    
    def restore_chat(self, chat_id: UUID, user_id: str) -> Optional[ChatPublic]:
        """
        Restore a soft-deleted chat.
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            
        Returns:
            Restored ChatPublic instance or None if not found or user doesn't own it
        """
        chat = self.repository.restore(chat_id, user_id)
        if not chat:
            return None
        return ChatPublic.model_validate(chat)
    
    def count_user_chats(self, user_id: str, include_deleted: bool = False) -> int:
        """
        Count total chats for a user.
        
        Args:
            user_id: User ID string
            include_deleted: If True, include soft-deleted chats in count
            
        Returns:
            Total count of chats
        """
        return self.repository.count_by_user(user_id, include_deleted=include_deleted)
    
    def count_active_chats(self, user_id: str) -> int:
        """
        Count active (non-deleted) chats for a user.
        
        Args:
            user_id: User ID string
            
        Returns:
            Count of active chats
        """
        return self.count_user_chats(user_id, include_deleted=False)
    
    def count_deleted_chats(self, user_id: str) -> int:
        """
        Count soft-deleted chats for a user.
        
        Args:
            user_id: User ID string
            
        Returns:
            Count of deleted chats
        """
        total = self.count_user_chats(user_id, include_deleted=True)
        active = self.count_user_chats(user_id, include_deleted=False)
        return total - active
    
    def get_deleted_chats(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[ChatPublic]:
        """
        Get all soft-deleted chats for a user.
        
        Args:
            user_id: User ID string
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of deleted ChatPublic instances
        """
        all_chats = self.repository.get_all_by_user(
            user_id,
            skip=0,
            limit=10000,  # Get all to filter
            include_deleted=True
        )
        deleted_chats = [chat for chat in all_chats if chat.is_deleted]
        
        # Apply pagination manually
        paginated = deleted_chats[skip:skip + limit] if skip < len(deleted_chats) else []
        
        return [ChatPublic.model_validate(chat) for chat in paginated]
    
    def update_chat_title(
        self,
        chat_id: UUID,
        user_id: str,
        title: str
    ) -> Optional[ChatPublic]:
        """
        Update only the title of a chat.
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            title: New title
            
        Returns:
            Updated ChatPublic instance or None if not found
        """
        update_data = ChatUpdate(title=title)
        return self.update_chat(chat_id, user_id, update_data)
    
    def update_chat_summary(
        self,
        chat_id: UUID,
        user_id: str,
        summary: str
    ) -> Optional[ChatPublic]:
        """
        Update only the summary of a chat.
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            summary: New summary
            
        Returns:
            Updated ChatPublic instance or None if not found
        """
        update_data = ChatUpdate(summary=summary)
        return self.update_chat(chat_id, user_id, update_data)
    
    def chat_exists(self, chat_id: UUID, user_id: str) -> bool:
        """
        Check if a chat exists for a user.
        
        Args:
            chat_id: Chat UUID
            user_id: User ID string to verify ownership
            
        Returns:
            True if chat exists and user owns it, False otherwise
        """
        return self.repository.get_by_id(chat_id, user_id) is not None
    
    def bulk_delete_chats(self, chat_ids: list[UUID], user_id: str) -> dict[str, int]:
        """
        Soft delete multiple chats at once.
        
        Args:
            chat_ids: List of chat UUIDs
            user_id: User ID string to verify ownership
            
        Returns:
            Dictionary with counts of successful and failed deletions
        """
        successful = 0
        failed = 0
        
        for chat_id in chat_ids:
            if self.repository.soft_delete(chat_id, user_id):
                successful += 1
            else:
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(chat_ids)
        }
    
    def bulk_restore_chats(self, chat_ids: list[UUID], user_id: str) -> dict[str, int]:
        """
        Restore multiple soft-deleted chats at once.
        
        Args:
            chat_ids: List of chat UUIDs
            user_id: User ID string to verify ownership
            
        Returns:
            Dictionary with counts of successful and failed restorations
        """
        successful = 0
        failed = 0
        
        for chat_id in chat_ids:
            if self.repository.restore(chat_id, user_id) is not None:
                successful += 1
            else:
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(chat_ids)
        }
    
    def bulk_permanently_delete_chats(
        self,
        chat_ids: list[UUID],
        user_id: str
    ) -> dict[str, int]:
        """
        Permanently delete multiple chats at once.
        
        Args:
            chat_ids: List of chat UUIDs
            user_id: User ID string to verify ownership
            
        Returns:
            Dictionary with counts of successful and failed deletions
        """
        successful = 0
        failed = 0
        
        for chat_id in chat_ids:
            if self.repository.hard_delete(chat_id, user_id):
                successful += 1
            else:
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(chat_ids)
        }
