from typing import Optional
from uuid import UUID
from sqlmodel import Session, select, desc
from app.models import Chat, ChatCreate, ChatUpdate
from datetime import datetime, timezone


class ChatRepository:
    """Repository for Chat CRUD operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, user_id: UUID, chat_data: ChatCreate) -> Chat:
        """
        Create a new chat.
        
        Args:
            user_id: User UUID (from authenticated user)
            chat_data: Chat creation data
            
        Returns:
            Created chat instance
        """
        chat = Chat(
            user_id=user_id,
            **chat_data.model_dump()
        )
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)
        return chat
    
    def get_by_id(self, chat_id: UUID, user_id: UUID) -> Optional[Chat]:
        """
        Get a chat by ID for a specific user.
        
        Args:
            chat_id: Chat UUID
            user_id: User UUID to verify ownership
            
        Returns:
            Chat instance or None if not found or user doesn't own it
        """
        statement = select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == user_id,
            Chat.is_deleted == False
        )
        return self.session.exec(statement).first()
    
    def get_all_by_user(
        self, 
        user_id: UUID,
        skip: int = 0, 
        limit: int = 100,
        include_deleted: bool = False
    ) -> list[Chat]:
        """
        Get all chats for a user with pagination.
        
        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: If True, include deleted chats
            
        Returns:
            List of chat instances
        """
        statement = select(Chat).where(Chat.user_id == user_id)
        
        if not include_deleted:
            statement = statement.where(Chat.is_deleted == False)
        
        statement = statement.order_by(desc(Chat.updated_at)).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
    
    def update(self, chat_id: UUID, user_id: UUID, chat_data: ChatUpdate) -> Optional[Chat]:
        """
        Update a chat.
        
        Args:
            chat_id: Chat UUID
            user_id: User UUID to verify ownership
            chat_data: Chat update data
            
        Returns:
            Updated chat instance or None if not found or user doesn't own it
        """
        chat = self.get_by_id(chat_id, user_id)
        if not chat:
            return None
        
        update_data = chat_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(chat, key, value)
        
        chat.updated_at = datetime.now(timezone.utc)
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)
        return chat
    
    def soft_delete(self, chat_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a chat (mark as deleted).
        
        Args:
            chat_id: Chat UUID
            user_id: User UUID to verify ownership
            
        Returns:
            True if deleted, False if not found or user doesn't own it
        """
        chat = self.get_by_id(chat_id, user_id)
        if not chat:
            return False
        
        chat.is_deleted = True
        chat.updated_at = datetime.now(timezone.utc)
        self.session.add(chat)
        self.session.commit()
        return True
    
    def hard_delete(self, chat_id: UUID, user_id: UUID) -> bool:
        """
        Hard delete a chat (permanently remove from database).
        
        Args:
            chat_id: Chat UUID
            user_id: User UUID to verify ownership
            
        Returns:
            True if deleted, False if not found or user doesn't own it
        """
        statement = select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == user_id
        )
        chat = self.session.exec(statement).first()
        if not chat:
            return False
        
        self.session.delete(chat)
        self.session.commit()
        return True
    
    def restore(self, chat_id: UUID, user_id: UUID) -> Optional[Chat]:
        """
        Restore a soft-deleted chat.
        
        Args:
            chat_id: Chat UUID
            user_id: User UUID to verify ownership
            
        Returns:
            Restored chat instance or None if not found or user doesn't own it
        """
        statement = select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == user_id,
            Chat.is_deleted
        )
        chat = self.session.exec(statement).first()
        if not chat:
            return None
        
        chat.is_deleted = False
        chat.updated_at = datetime.now(timezone.utc)
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)
        return chat
    
    def count_by_user(self, user_id: UUID, include_deleted: bool = False) -> int:
        """
        Count total chats for a user.
        
        Args:
            user_id: User UUID
            include_deleted: If True, include deleted chats in count
            
        Returns:
            Total count of chats
        """
        statement = select(Chat).where(Chat.user_id == user_id)
        
        if not include_deleted:
            statement = statement.where(Chat.is_deleted == False)
        
        results = self.session.exec(statement).all()
        return len(list(results))
