from typing import Optional
from uuid import UUID
from sqlmodel import Session, select, desc, col
from app.models import Message, MessageCreate, MessageUpdate, Model
from datetime import datetime, timezone


class MessageRepository:
    """Repository for Message CRUD operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, message_data: MessageCreate) -> Message:
        """
        Create a new message.
        
        Args:
            message_data: Message creation data
            
        Returns:
            Created message instance
        """
        message = Message.model_validate(message_data)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
    
    def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """
        Get a message by ID.
        
        Args:
            message_id: Message UUID
            
        Returns:
            Message instance or None if not found
        """
        statement = select(Message).where(Message.id == message_id, Message.is_deleted == False)
        return self.session.exec(statement).first()
    
    def get_with_model(self, message_id: UUID) -> Optional[tuple[Message, Model]]:
        """
        Get a message by ID with its associated model.
        
        Args:
            message_id: Message UUID
            
        Returns:
            Tuple of (Message, Model) or None if not found
        """
        statement = (
            select(Message, Model)
            .where(Message.model_id == Model.id)
            .where(Message.id == message_id, Message.is_deleted == False)
        )
        result = self.session.exec(statement).first()
        return result if result else None
    
    def get_all_by_chat(
        self, 
        chat_id: UUID,
        skip: int = 0, 
        limit: int = 100,
        include_deleted: bool = False
    ) -> list[Message]:
        """
        Get all messages for a chat with pagination.
        
        Args:
            chat_id: Chat UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: If True, include deleted messages
            
        Returns:
            List of message instances ordered by creation time
        """
        statement = select(Message).where(Message.chat_id == chat_id)
        
        if not include_deleted:
            statement = statement.where(Message.is_deleted == False)
        
        statement = statement.order_by(col(Message.created_at)).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
    
    def get_all_by_chat_with_model(
        self, 
        chat_id: UUID,
        skip: int = 0, 
        limit: int = 100,
        include_deleted: bool = False
    ) -> list[tuple[Message, Model]]:
        """
        Get all messages for a chat with their associated models.
        
        Args:
            chat_id: Chat UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: If True, include deleted messages
            
        Returns:
            List of (Message, Model) tuples ordered by creation time
        """
        statement = (
            select(Message, Model)
            .where(Message.model_id == Model.id)
            .where(Message.chat_id == chat_id)
        )
        
        if not include_deleted:
            statement = statement.where(Message.is_deleted == False)
        
        statement = statement.order_by(col(Message.created_at)).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
    
    def get_by_type(
        self, 
        chat_id: UUID, 
        message_type: str,
        skip: int = 0, 
        limit: int = 100
    ) -> list[Message]:
        """
        Get messages by type for a specific chat.
        
        Args:
            chat_id: Chat UUID
            message_type: Message type (user, ai, system)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of message instances
        """
        statement = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.type == message_type,
                Message.is_deleted == False
            )
            .order_by(col(Message.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())
    
    def update(self, message_id: UUID, message_data: MessageUpdate) -> Optional[Message]:
        """
        Update a message.
        
        Args:
            message_id: Message UUID
            message_data: Message update data
            
        Returns:
            Updated message instance or None if not found
        """
        message = self.get_by_id(message_id)
        if not message:
            return None
        
        update_data = message_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(message, key, value)
        
        message.updated_at = datetime.now(timezone.utc)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
    
    def update_feedback(self, message_id: UUID, feedback: str) -> Optional[Message]:
        """
        Update message feedback.
        
        Args:
            message_id: Message UUID
            feedback: Feedback value (positive/negative)
            
        Returns:
            Updated message instance or None if not found
        """
        message = self.get_by_id(message_id)
        if not message:
            return None
        
        message.feedback = feedback
        message.updated_at = datetime.now(timezone.utc)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
    
    def soft_delete(self, message_id: UUID) -> bool:
        """
        Soft delete a message (mark as deleted).
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
        """
        message = self.get_by_id(message_id)
        if not message:
            return False
        
        message.is_deleted = True
        message.updated_at = datetime.now(timezone.utc)
        self.session.add(message)
        self.session.commit()
        return True
    
    def hard_delete(self, message_id: UUID) -> bool:
        """
        Hard delete a message (permanently remove from database).
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
        """
        statement = select(Message).where(Message.id == message_id)
        message = self.session.exec(statement).first()
        if not message:
            return False
        
        self.session.delete(message)
        self.session.commit()
        return True
    
    def soft_delete_by_chat(self, chat_id: UUID) -> int:
        """
        Soft delete all messages in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Number of messages deleted
        """
        statement = select(Message).where(
            Message.chat_id == chat_id,
            Message.is_deleted == False
        )
        messages = self.session.exec(statement).all()
        
        count = 0
        for message in messages:
            message.is_deleted = True
            message.updated_at = datetime.now(timezone.utc)
            self.session.add(message)
            count += 1
        
        if count > 0:
            self.session.commit()
        
        return count
    
    def count_by_chat(self, chat_id: UUID, include_deleted: bool = False) -> int:
        """
        Count total messages in a chat.
        
        Args:
            chat_id: Chat UUID
            include_deleted: If True, include deleted messages in count
            
        Returns:
            Total count of messages
        """
        statement = select(Message).where(Message.chat_id == chat_id)
        
        if not include_deleted:
            statement = statement.where(Message.is_deleted == False)
        
        results = self.session.exec(statement).all()
        return len(list(results))
    
    def get_latest_by_chat(self, chat_id: UUID) -> Optional[Message]:
        """
        Get the latest message in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Latest message instance or None if no messages
        """
        statement = (
            select(Message)
            .where(Message.chat_id == chat_id, Message.is_deleted == False)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        return self.session.exec(statement).first()
    
    def calculate_total_tokens(self, chat_id: UUID) -> int:
        """
        Calculate total tokens used in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Total token count
        """
        statement = select(Message).where(
            Message.chat_id == chat_id,
            Message.is_deleted == False
        )
        messages = self.session.exec(statement).all()
        return sum(msg.tokens or 0 for msg in messages if msg.tokens is not None)
