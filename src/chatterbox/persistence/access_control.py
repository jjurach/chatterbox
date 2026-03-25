"""
User context and access control for multi-user isolation.

Ensures users only access their own conversations and prevents data leakage
across user boundaries. Provides RBAC framework for future admin/user roles.

Features:
- Users only access their conversations
- No cross-user data leakage
- Automatic query filtering by user_id
- RBAC framework (roles table + permissions)
- Context enforcement middleware

Reference: docs/context-retrieval-guide.md
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
)
from chatterbox.persistence.schema import Conversation, Message, User

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles for RBAC.

    Attributes:
        ADMIN: Full access to all conversations and users.
        USER: Access to own conversations only.
        GUEST: Read-only access to shared conversations.
    """

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class Permission(str, Enum):
    """Permissions that can be assigned to roles.

    Attributes:
        READ: Can read messages.
        WRITE: Can create messages.
        DELETE: Can delete messages.
        MANAGE_USERS: Can create/delete users.
        VIEW_ALL: Can view all conversations (admin only).
    """

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    VIEW_ALL = "view_all"


class RolePermissions:
    """Predefined role permissions."""

    DEFAULT_PERMISSIONS = {
        UserRole.ADMIN: {
            Permission.READ,
            Permission.WRITE,
            Permission.DELETE,
            Permission.MANAGE_USERS,
            Permission.VIEW_ALL,
        },
        UserRole.USER: {
            Permission.READ,
            Permission.WRITE,
            Permission.DELETE,
        },
        UserRole.GUEST: {
            Permission.READ,
        },
    }


class UserContext:
    """Context for the current user making a request.

    Attributes:
        user_id: The user's UUID.
        username: The user's username.
        role: The user's role (admin, user, guest).
        permissions: Set of permissions for the user.
    """

    def __init__(
        self,
        user_id: str,
        username: str,
        role: UserRole = UserRole.USER,
        permissions: Optional[set[Permission]] = None,
    ):
        """Initialize user context.

        Args:
            user_id: The user's UUID.
            username: The user's username.
            role: The user's role (default: USER).
            permissions: Set of permissions (uses default for role if None).
        """
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions or RolePermissions.DEFAULT_PERMISSIONS.get(
            role, set()
        )

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: The permission to check.

        Returns:
            True if the user has the permission.
        """
        return permission in self.permissions

    def is_admin(self) -> bool:
        """Check if user is an admin.

        Returns:
            True if the user role is ADMIN.
        """
        return self.role == UserRole.ADMIN

    def __repr__(self) -> str:
        return f"<UserContext(user_id={self.user_id!r}, role={self.role!r})>"


class AccessControlMiddleware:
    """Middleware for enforcing user context and access control.

    Automatically filters queries to respect user_id boundaries.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the middleware.

        Args:
            session: AsyncSession for database operations.
        """
        self.session = session

    async def require_user_context(self, user_id: str) -> UserContext:
        """Create a user context with proper validation.

        Verifies that the user exists and loads their role.

        Args:
            user_id: The user's UUID.

        Returns:
            UserContext for the user.

        Raises:
            ValueError: If user doesn't exist.
        """
        # Verify user exists
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Default role is USER
        # In future, load from database user_role column
        role = UserRole.USER

        context = UserContext(
            user_id=user.id,
            username=user.username,
            role=role,
        )

        logger.debug("Created user context: %s", context)
        return context

    async def get_user_conversations(
        self,
        user_context: UserContext,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Conversation]:
        """Get conversations for a user.

        Only returns conversations owned by the user (unless user is admin).

        Args:
            user_context: The user context.
            limit: Maximum results.
            offset: Number to skip.

        Returns:
            List of Conversation objects.
        """
        # Admins can see all conversations
        if user_context.is_admin():
            result = await self.session.execute(
                select(Conversation).limit(limit).offset(offset)
            )
            return result.scalars().all()

        # Regular users can only see their own conversations
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_context.user_id)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_user_conversation(
        self,
        user_context: UserContext,
        conversation_id: str,
    ) -> Conversation | None:
        """Get a specific conversation, enforcing access control.

        Returns None if user doesn't have access to the conversation.

        Args:
            user_context: The user context.
            conversation_id: The conversation UUID.

        Returns:
            Conversation object or None if not found/not accessible.
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()

        if not conversation:
            return None

        # Admins can access any conversation
        if user_context.is_admin():
            return conversation

        # Regular users can only access their own conversations
        if conversation.user_id == user_context.user_id:
            return conversation

        logger.warning(
            "Access denied: user %s attempted to access conversation %s owned by %s",
            user_context.user_id,
            conversation_id,
            conversation.user_id,
        )
        return None

    async def get_user_messages(
        self,
        user_context: UserContext,
        conversation_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages from a conversation, enforcing access control.

        Returns empty list if user doesn't have access.

        Args:
            user_context: The user context.
            conversation_id: The conversation UUID.
            limit: Maximum messages.

        Returns:
            List of Message objects.
        """
        # Verify user has access to conversation
        conversation = await self.get_user_conversation(user_context, conversation_id)
        if not conversation:
            return []

        # Check for read permission
        if not user_context.has_permission(Permission.READ):
            logger.warning(
                "Access denied: user %s lacks READ permission",
                user_context.user_id,
            )
            return []

        # Get messages
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
            .limit(limit)
        )
        return result.scalars().all()

    async def add_message(
        self,
        user_context: UserContext,
        conversation_id: str,
        role: str,
        content: str,
    ) -> Message | None:
        """Add a message, enforcing access control.

        Returns None if user doesn't have access or lacks WRITE permission.

        Args:
            user_context: The user context.
            conversation_id: The conversation UUID.
            role: Message role.
            content: Message content.

        Returns:
            Message object or None if access denied.
        """
        # Verify access
        conversation = await self.get_user_conversation(user_context, conversation_id)
        if not conversation:
            return None

        # Check permission
        if not user_context.has_permission(Permission.WRITE):
            logger.warning(
                "Access denied: user %s lacks WRITE permission",
                user_context.user_id,
            )
            return None

        # Add message
        msg_repo = MessageRepository(self.session)
        message = await msg_repo.add(conversation_id, role, content)

        logger.info(
            "User %s added message to conversation %s",
            user_context.user_id,
            conversation_id,
        )

        return message

    async def delete_message(
        self,
        user_context: UserContext,
        conversation_id: str,
        message_id: str,
    ) -> bool:
        """Delete a message, enforcing access control.

        Returns False if user doesn't have access or lacks DELETE permission.

        Args:
            user_context: The user context.
            conversation_id: The conversation UUID.
            message_id: The message UUID.

        Returns:
            True if deleted, False if access denied.
        """
        # Verify access
        conversation = await self.get_user_conversation(user_context, conversation_id)
        if not conversation:
            return False

        # Check permission
        if not user_context.has_permission(Permission.DELETE):
            logger.warning(
                "Access denied: user %s lacks DELETE permission",
                user_context.user_id,
            )
            return False

        # Delete message
        msg_repo = MessageRepository(self.session)
        result = await msg_repo.delete(message_id)

        if result:
            logger.info(
                "User %s deleted message %s from conversation %s",
                user_context.user_id,
                message_id,
                conversation_id,
            )

        return result

    async def list_conversations_by_role(
        self,
        user_context: UserContext,
    ) -> dict[str, Any]:
        """Get conversation statistics by role.

        Useful for admin dashboards and user activity tracking.

        Args:
            user_context: The user context (must be admin).

        Returns:
            Dict with role-based statistics.

        Raises:
            PermissionError: If user is not admin.
        """
        if not user_context.is_admin():
            raise PermissionError("Only admins can view global statistics")

        # Count conversations by user
        result = await self.session.execute(select(Conversation))
        conversations = result.scalars().all()

        stats = {
            "total_conversations": len(conversations),
            "by_user": {},
        }

        # Group by user
        for conv in conversations:
            user_id = conv.user_id or "anonymous"
            if user_id not in stats["by_user"]:
                stats["by_user"][user_id] = 0
            stats["by_user"][user_id] += 1

        return stats
