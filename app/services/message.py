from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.repositories.message import MessageRepository
from app.repositories.chat import ChatRepository
from app.repositories.model import ModelRepository
from app.models import (
    Message, 
    MessageCreate, 
    MessageUpdate, 
    MessagePublic,
    ModelPublic,
    ChatCreate
)


class MessageService:
    """Service layer for Message business logic."""
    
    def __init__(self, session: Session):
        self.message_repository = MessageRepository(session)
        self.chat_repository = ChatRepository(session)
        self.model_repository = ModelRepository(session)
    
    def create_message(self, message_data: MessageCreate, user_id: Optional[str] = None) -> Optional[MessagePublic]:
        """
        Create a new message.
        
        Args:
            message_data: Message creation data
            user_id: Optional user ID string - required if auto-creating a chat
            
        Returns:
            Created message as MessagePublic or None if validation fails
            
        Raises:
            ValueError: If model doesn't exist or is disabled, or if chat doesn't exist
        """
        # Verify model exists and is enabled
        model = self.model_repository.get_by_id(message_data.model_id)
        if not model:
            raise ValueError(f"Model with ID '{message_data.model_id}' does not exist")
        if not model.is_enabled:
            raise ValueError(f"Model '{model.name}' is currently disabled")
        
        # Verify chat exists (without user_id check for internal use)
        from sqlmodel import select
        from app.models import Chat
        statement = select(Chat).where(Chat.id == message_data.chat_id)
        chat = self.chat_repository.session.exec(statement).first()
        if not chat:
            raise ValueError(f"Chat with ID '{message_data.chat_id}' does not exist")
        
        message = self.message_repository.create(message_data)
        
        # Get message with model for proper serialization
        result = self.message_repository.get_with_model(message.id)
        if not result:
            return None
        
        message_obj, model_obj = result
        # Construct MessagePublic with all fields including the model
        message_public = MessagePublic.model_construct(
            id=message_obj.id,
            chat_id=message_obj.chat_id,
            model_id=message_obj.model_id,
            type=message_obj.type,
            content=message_obj.content,
            tokens=message_obj.tokens,
            feedback=message_obj.feedback,
            is_deleted=message_obj.is_deleted,
            created_at=message_obj.created_at,
            updated_at=message_obj.updated_at,
            model=ModelPublic.model_validate(model_obj)
        )
        return message_public
    
    def create_message_with_auto_chat(
        self,
        user_id: str,
        model_id: UUID,
        content: str,
        message_type: str = "user",
        tokens: Optional[int] = None,
        chat_title: Optional[str] = None
    ) -> tuple[MessagePublic, UUID]:
        """
        Create a new message and automatically create a chat if needed.
        This is useful for starting a new conversation.
        
        Args:
            user_id: User ID string
            model_id: Model UUID
            content: Message content
            message_type: Message type (default: "user")
            tokens: Optional token count
            chat_title: Optional chat title (defaults to truncated content)
            
        Returns:
            Tuple of (created MessagePublic, chat_id)
            
        Raises:
            ValueError: If model doesn't exist or is disabled
        """
        # Verify model exists and is enabled
        model = self.model_repository.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model with ID '{model_id}' does not exist")
        if not model.is_enabled:
            raise ValueError(f"Model '{model.name}' is currently disabled")
        
        # Generate chat title from content if not provided
        if not chat_title:
            # Use first 50 characters of content as title
            chat_title = content[:50] + "..." if len(content) > 50 else content
        
        # Create the chat
        chat_data = ChatCreate(title=chat_title)
        chat = self.chat_repository.create(user_id, chat_data)
        
        # Create the message
        message_data = MessageCreate(
            chat_id=chat.id,
            model_id=model_id,
            type=message_type,
            content=content,
            tokens=tokens
        )
        message = self.message_repository.create(message_data)
        
        # Get message with model for proper serialization
        result = self.message_repository.get_with_model(message.id)
        if not result:
            raise ValueError("Failed to retrieve created message")
        
        message_obj, model_obj = result
        message_public = MessagePublic.model_construct(
            id=message_obj.id,
            chat_id=message_obj.chat_id,
            model_id=message_obj.model_id,
            type=message_obj.type,
            content=message_obj.content,
            tokens=message_obj.tokens,
            feedback=message_obj.feedback,
            is_deleted=message_obj.is_deleted,
            created_at=message_obj.created_at,
            updated_at=message_obj.updated_at,
            model=ModelPublic.model_validate(model_obj)
        )
        
        return message_public, chat.id
    
    def get_message_by_id(self, message_id: UUID) -> Optional[MessagePublic]:
        """
        Get a message by ID with its associated model.
        
        Args:
            message_id: Message UUID
            
        Returns:
            MessagePublic instance or None if not found
        """
        result = self.message_repository.get_with_model(message_id)
        if not result:
            return None
        
        message, model = result
        message_public = MessagePublic.model_construct(
            id=message.id,
            chat_id=message.chat_id,
            model_id=message.model_id,
            type=message.type,
            content=message.content,
            tokens=message.tokens,
            feedback=message.feedback,
            is_deleted=message.is_deleted,
            created_at=message.created_at,
            updated_at=message.updated_at,
            model=ModelPublic.model_validate(model)
        )
        return message_public
    
    def get_chat_messages(
        self,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> list[MessagePublic]:
        """
        Get all messages for a chat with pagination.
        
        Args:
            chat_id: Chat UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: If True, include soft-deleted messages
            
        Returns:
            List of MessagePublic instances ordered by creation time
        """
        results = self.message_repository.get_all_by_chat_with_model(
            chat_id,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted
        )
        
        message_publics = []
        for message, model in results:
            message_public = MessagePublic.model_construct(
                id=message.id,
                chat_id=message.chat_id,
                model_id=message.model_id,
                type=message.type,
                content=message.content,
                tokens=message.tokens,
                feedback=message.feedback,
                is_deleted=message.is_deleted,
                created_at=message.created_at,
                updated_at=message.updated_at,
                model=ModelPublic.model_validate(model)
            )
            message_publics.append(message_public)
        
        return message_publics
    
    def get_active_messages(
        self,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[MessagePublic]:
        """
        Get all active (non-deleted) messages for a chat.
        
        Args:
            chat_id: Chat UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active MessagePublic instances
        """
        return self.get_chat_messages(
            chat_id,
            skip=skip,
            limit=limit,
            include_deleted=False
        )
    
    def get_messages_by_type(
        self,
        chat_id: UUID,
        message_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[MessagePublic]:
        """
        Get messages by type for a specific chat.
        
        Args:
            chat_id: Chat UUID
            message_type: Message type (user, ai, system)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of MessagePublic instances of the specified type
        """
        messages = self.message_repository.get_by_type(
            chat_id,
            message_type,
            skip=skip,
            limit=limit
        )
        
        # Get models for each message
        message_publics = []
        for message in messages:
            result = self.message_repository.get_with_model(message.id)
            if result:
                msg, model = result
                message_public = MessagePublic.model_construct(
                    id=msg.id,
                    chat_id=msg.chat_id,
                    model_id=msg.model_id,
                    type=msg.type,
                    content=msg.content,
                    tokens=msg.tokens,
                    feedback=msg.feedback,
                    is_deleted=msg.is_deleted,
                    created_at=msg.created_at,
                    updated_at=msg.updated_at,
                    model=ModelPublic.model_validate(model)
                )
                message_publics.append(message_public)
        
        return message_publics
    
    def get_user_messages(
        self,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[MessagePublic]:
        """
        Get all user messages for a chat.
        
        Args:
            chat_id: Chat UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of user MessagePublic instances
        """
        return self.get_messages_by_type(chat_id, "user", skip, limit)
    
    def get_ai_messages(
        self,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[MessagePublic]:
        """
        Get all AI messages for a chat.
        
        Args:
            chat_id: Chat UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of AI MessagePublic instances
        """
        return self.get_messages_by_type(chat_id, "ai", skip, limit)
    
    def update_message(
        self,
        message_id: UUID,
        message_data: MessageUpdate
    ) -> Optional[MessagePublic]:
        """
        Update a message.
        
        Args:
            message_id: Message UUID
            message_data: Message update data
            
        Returns:
            Updated MessagePublic instance or None if not found
            
        Raises:
            ValueError: If trying to update to a disabled model
        """
        # If updating model_id, verify it exists and is enabled
        if message_data.model_id is not None:
            model = self.model_repository.get_by_id(message_data.model_id)
            if not model:
                raise ValueError(f"Model with ID '{message_data.model_id}' does not exist")
            if not model.is_enabled:
                raise ValueError(f"Model '{model.name}' is currently disabled")
        
        message = self.message_repository.update(message_id, message_data)
        if not message:
            return None
        
        # Get with model for proper serialization
        result = self.message_repository.get_with_model(message.id)
        if not result:
            return None
        
        msg, model = result
        message_public = MessagePublic.model_construct(
            id=msg.id,
            chat_id=msg.chat_id,
            model_id=msg.model_id,
            type=msg.type,
            content=msg.content,
            tokens=msg.tokens,
            feedback=msg.feedback,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            model=ModelPublic.model_validate(model)
        )
        return message_public
    
    def update_message_content(
        self,
        message_id: UUID,
        content: str
    ) -> Optional[MessagePublic]:
        """
        Update only the content of a message.
        
        Args:
            message_id: Message UUID
            content: New content
            
        Returns:
            Updated MessagePublic instance or None if not found
        """
        update_data = MessageUpdate(content=content)
        return self.update_message(message_id, update_data)
    
    def update_message_feedback(
        self,
        message_id: UUID,
        feedback: str
    ) -> Optional[MessagePublic]:
        """
        Update message feedback (positive/negative).
        
        Args:
            message_id: Message UUID
            feedback: Feedback value
            
        Returns:
            Updated MessagePublic instance or None if not found
        """
        message = self.message_repository.update_feedback(message_id, feedback)
        if not message:
            return None
        
        result = self.message_repository.get_with_model(message.id)
        if not result:
            return None
        
        msg, model = result
        message_public = MessagePublic.model_construct(
            id=msg.id,
            chat_id=msg.chat_id,
            model_id=msg.model_id,
            type=msg.type,
            content=msg.content,
            tokens=msg.tokens,
            feedback=msg.feedback,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            model=ModelPublic.model_validate(model)
        )
        return message_public
    
    def delete_message(self, message_id: UUID) -> bool:
        """
        Soft delete a message (can be restored by getting with include_deleted).
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
        """
        return self.message_repository.soft_delete(message_id)
    
    def permanently_delete_message(self, message_id: UUID) -> bool:
        """
        Permanently delete a message (cannot be restored).
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
        """
        return self.message_repository.hard_delete(message_id)
    
    def delete_chat_messages(self, chat_id: UUID) -> int:
        """
        Soft delete all messages in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Number of messages deleted
        """
        return self.message_repository.soft_delete_by_chat(chat_id)
    
    def count_chat_messages(
        self,
        chat_id: UUID,
        include_deleted: bool = False
    ) -> int:
        """
        Count total messages in a chat.
        
        Args:
            chat_id: Chat UUID
            include_deleted: If True, include soft-deleted messages in count
            
        Returns:
            Total count of messages
        """
        return self.message_repository.count_by_chat(chat_id, include_deleted)
    
    def count_active_messages(self, chat_id: UUID) -> int:
        """
        Count active (non-deleted) messages in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Count of active messages
        """
        return self.count_chat_messages(chat_id, include_deleted=False)
    
    def get_latest_message(self, chat_id: UUID) -> Optional[MessagePublic]:
        """
        Get the latest message in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Latest MessagePublic instance or None if no messages
        """
        message = self.message_repository.get_latest_by_chat(chat_id)
        if not message:
            return None
        
        result = self.message_repository.get_with_model(message.id)
        if not result:
            return None
        
        msg, model = result
        message_public = MessagePublic.model_construct(
            id=msg.id,
            chat_id=msg.chat_id,
            model_id=msg.model_id,
            type=msg.type,
            content=msg.content,
            tokens=msg.tokens,
            feedback=msg.feedback,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            model=ModelPublic.model_validate(model)
        )
        return message_public
    
    def calculate_chat_tokens(self, chat_id: UUID) -> int:
        """
        Calculate total tokens used in a chat.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Total token count
        """
        return self.message_repository.calculate_total_tokens(chat_id)
    
    def calculate_chat_cost(self, chat_id: UUID) -> float:
        """
        Calculate the total cost for a chat based on tokens and model pricing.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Total cost in dollars
        """
        messages = self.message_repository.get_all_by_chat_with_model(
            chat_id,
            skip=0,
            limit=10000,  # Get all messages
            include_deleted=False
        )
        
        total_cost = 0.0
        for message, model in messages:
            if message.tokens:
                # price_per_million_tokens * (tokens / 1_000_000)
                cost = float(model.price_per_million_tokens) * (message.tokens / 1_000_000)
                total_cost += cost
        
        return total_cost
    
    def message_exists(self, message_id: UUID) -> bool:
        """
        Check if a message exists.
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if message exists, False otherwise
        """
        return self.message_repository.get_by_id(message_id) is not None
    
    def get_conversation_summary(self, chat_id: UUID) -> dict:
        """
        Get a summary of the conversation including counts and tokens.
        
        Args:
            chat_id: Chat UUID
            
        Returns:
            Dictionary with conversation statistics
        """
        total_messages = self.count_active_messages(chat_id)
        user_messages = len(self.message_repository.get_by_type(chat_id, "user"))
        ai_messages = len(self.message_repository.get_by_type(chat_id, "ai"))
        system_messages = len(self.message_repository.get_by_type(chat_id, "system"))
        total_tokens = self.calculate_chat_tokens(chat_id)
        total_cost = self.calculate_chat_cost(chat_id)
        
        latest_message = self.get_latest_message(chat_id)
        
        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "system_messages": system_messages,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "latest_message_at": latest_message.created_at if latest_message else None
        }
    
    def bulk_delete_messages(self, message_ids: list[UUID]) -> dict[str, int]:
        """
        Soft delete multiple messages at once.
        
        Args:
            message_ids: List of message UUIDs
            
        Returns:
            Dictionary with counts of successful and failed deletions
        """
        successful = 0
        failed = 0
        
        for message_id in message_ids:
            if self.message_repository.soft_delete(message_id):
                successful += 1
            else:
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(message_ids)
        }
    
    def bulk_permanently_delete_messages(self, message_ids: list[UUID]) -> dict[str, int]:
        """
        Permanently delete multiple messages at once.
        
        Args:
            message_ids: List of message UUIDs
            
        Returns:
            Dictionary with counts of successful and failed deletions
        """
        successful = 0
        failed = 0
        
        for message_id in message_ids:
            if self.message_repository.hard_delete(message_id):
                successful += 1
            else:
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(message_ids)
        }
    
    def get_messages_with_feedback(
        self,
        chat_id: UUID,
        feedback_type: Optional[str] = None
    ) -> list[MessagePublic]:
        """
        Get messages that have feedback, optionally filtered by feedback type.
        
        Args:
            chat_id: Chat UUID
            feedback_type: Optional filter for 'positive' or 'negative'
            
        Returns:
            List of MessagePublic instances with feedback
        """
        all_messages = self.get_chat_messages(chat_id, skip=0, limit=10000)
        
        if feedback_type:
            return [msg for msg in all_messages if msg.feedback == feedback_type]
        else:
            return [msg for msg in all_messages if msg.feedback is not None]
