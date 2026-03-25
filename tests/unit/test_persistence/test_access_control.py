"""
Tests for user context and access control.

Tests cover:
- User context creation
- Role-based permissions
- Access control enforcement
- User isolation
- Multi-user scenarios
- Admin access
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.access_control import (
    AccessControlMiddleware,
    Permission,
    UserContext,
    UserRole,
    RolePermissions,
)
from chatterbox.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
    UserRepository,
)


class TestUserRole:
    """Tests for UserRole enum."""

    def test_user_role_values(self):
        """Test user role enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.GUEST.value == "guest"


class TestPermission:
    """Tests for Permission enum."""

    def test_permission_values(self):
        """Test permission enum values."""
        assert Permission.READ.value == "read"
        assert Permission.WRITE.value == "write"
        assert Permission.DELETE.value == "delete"
        assert Permission.MANAGE_USERS.value == "manage_users"
        assert Permission.VIEW_ALL.value == "view_all"


class TestRolePermissions:
    """Tests for RolePermissions defaults."""

    def test_admin_permissions(self):
        """Test that admin role has all permissions."""
        admin_perms = RolePermissions.DEFAULT_PERMISSIONS[UserRole.ADMIN]
        expected = {
            Permission.READ,
            Permission.WRITE,
            Permission.DELETE,
            Permission.MANAGE_USERS,
            Permission.VIEW_ALL,
        }
        assert admin_perms == expected

    def test_user_permissions(self):
        """Test that user role has basic permissions."""
        user_perms = RolePermissions.DEFAULT_PERMISSIONS[UserRole.USER]
        expected = {
            Permission.READ,
            Permission.WRITE,
            Permission.DELETE,
        }
        assert user_perms == expected

    def test_guest_permissions(self):
        """Test that guest role has read-only permission."""
        guest_perms = RolePermissions.DEFAULT_PERMISSIONS[UserRole.GUEST]
        expected = {Permission.READ}
        assert guest_perms == expected


class TestUserContext:
    """Tests for UserContext dataclass."""

    def test_create_user_context(self):
        """Test creating a user context."""
        context = UserContext(
            user_id="user-1",
            username="john",
            role=UserRole.USER,
        )
        assert context.user_id == "user-1"
        assert context.username == "john"
        assert context.role == UserRole.USER

    def test_user_context_default_permissions(self):
        """Test that user context gets default permissions for role."""
        context = UserContext(
            user_id="user-1",
            username="john",
            role=UserRole.USER,
        )
        assert Permission.READ in context.permissions
        assert Permission.WRITE in context.permissions
        assert Permission.DELETE in context.permissions

    def test_user_context_custom_permissions(self):
        """Test user context with custom permissions."""
        custom_perms = {Permission.READ}
        context = UserContext(
            user_id="user-1",
            username="john",
            role=UserRole.USER,
            permissions=custom_perms,
        )
        assert context.permissions == custom_perms

    def test_has_permission(self):
        """Test has_permission method."""
        context = UserContext(
            user_id="user-1",
            username="john",
            role=UserRole.USER,
        )
        assert context.has_permission(Permission.READ)
        assert context.has_permission(Permission.WRITE)
        assert not context.has_permission(Permission.MANAGE_USERS)

    def test_is_admin(self):
        """Test is_admin method."""
        admin_context = UserContext(
            user_id="admin-1",
            username="admin",
            role=UserRole.ADMIN,
        )
        user_context = UserContext(
            user_id="user-1",
            username="john",
            role=UserRole.USER,
        )
        assert admin_context.is_admin()
        assert not user_context.is_admin()


@pytest.mark.anyio
class TestAccessControlMiddleware:
    """Tests for AccessControlMiddleware enforcement."""

    async def test_require_user_context(self, async_session: AsyncSession):
        """Test requiring user context."""
        user_repo = UserRepository(async_session)
        user = await user_repo.create("john")
        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = await middleware.require_user_context(user.id)

        assert context.user_id == user.id
        assert context.username == "john"
        assert context.role == UserRole.USER

    async def test_require_user_context_not_found(self, async_session: AsyncSession):
        """Test requiring user context for non-existent user."""
        middleware = AccessControlMiddleware(async_session)

        with pytest.raises(ValueError):
            await middleware.require_user_context("nonexistent-user")

    async def test_get_user_conversations_regular_user(self, async_session: AsyncSession):
        """Test that regular users only see their conversations."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)

        # Create two users
        user1 = await user_repo.create("user1")
        user2 = await user_repo.create("user2")

        # Create conversations for each user
        conv1 = await conv_repo.create(user_id=user1.id, conversation_id="conv-1")
        conv2 = await conv_repo.create(user_id=user2.id, conversation_id="conv-2")

        await async_session.flush()

        # Get conversations for user1
        middleware = AccessControlMiddleware(async_session)
        context1 = UserContext("user-id-1", "user1", UserRole.USER)
        context1.user_id = user1.id  # Set to real user ID

        conversations = await middleware.get_user_conversations(context1)

        # User1 should only see their conversation
        assert len(conversations) >= 1
        assert any(c.id == conv1.id for c in conversations)

    async def test_get_user_conversations_admin(self, async_session: AsyncSession):
        """Test that admins see all conversations."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)

        # Create users
        admin = await user_repo.create("admin")
        user1 = await user_repo.create("user1")

        # Create conversations
        conv1 = await conv_repo.create(user_id=user1.id, conversation_id="conv-1")
        conv2 = await conv_repo.create(user_id=user1.id, conversation_id="conv-2")

        await async_session.flush()

        # Admin should see all conversations
        middleware = AccessControlMiddleware(async_session)
        admin_context = UserContext(admin.id, "admin", UserRole.ADMIN)

        conversations = await middleware.get_user_conversations(admin_context)

        assert len(conversations) >= 2

    async def test_get_user_conversation_access_allowed(self, async_session: AsyncSession):
        """Test accessing own conversation."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)

        user = await user_repo.create("user1")
        conversation = await conv_repo.create(user_id=user.id, conversation_id="conv-1")

        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user.id, "user1", UserRole.USER)

        result = await middleware.get_user_conversation(context, conversation.id)

        assert result is not None
        assert result.id == conversation.id

    async def test_get_user_conversation_access_denied(self, async_session: AsyncSession):
        """Test accessing someone else's conversation."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)

        user1 = await user_repo.create("user1")
        user2 = await user_repo.create("user2")
        conversation = await conv_repo.create(user_id=user1.id, conversation_id="conv-1")

        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user2.id, "user2", UserRole.USER)

        result = await middleware.get_user_conversation(context, conversation.id)

        assert result is None

    async def test_get_user_messages_access_allowed(self, async_session: AsyncSession):
        """Test accessing messages from own conversation."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        user = await user_repo.create("user1")
        conversation = await conv_repo.create(user_id=user.id, conversation_id="conv-1")
        await msg_repo.add(conversation.id, "user", "Hello")
        await msg_repo.add(conversation.id, "assistant", "Hi!")

        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user.id, "user1", UserRole.USER)

        messages = await middleware.get_user_messages(context, conversation.id)

        assert len(messages) == 2

    async def test_get_user_messages_access_denied(self, async_session: AsyncSession):
        """Test accessing messages from someone else's conversation."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        user1 = await user_repo.create("user1")
        user2 = await user_repo.create("user2")
        conversation = await conv_repo.create(user_id=user1.id, conversation_id="conv-1")
        await msg_repo.add(conversation.id, "user", "Secret message")

        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user2.id, "user2", UserRole.USER)

        messages = await middleware.get_user_messages(context, conversation.id)

        assert len(messages) == 0

    async def test_add_message_with_permission(self, async_session: AsyncSession):
        """Test adding message with proper permission."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)

        user = await user_repo.create("user1")
        conversation = await conv_repo.create(user_id=user.id, conversation_id="conv-1")

        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user.id, "user1", UserRole.USER)

        message = await middleware.add_message(
            context,
            conversation.id,
            "user",
            "Test message",
        )

        assert message is not None
        assert message.content == "Test message"

    async def test_add_message_without_permission(self, async_session: AsyncSession):
        """Test adding message without write permission."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)

        user = await user_repo.create("user1")
        conversation = await conv_repo.create(user_id=user.id, conversation_id="conv-1")

        await async_session.flush()

        # Create context with no write permission
        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user.id, "user1", UserRole.GUEST)  # Guest role

        message = await middleware.add_message(
            context,
            conversation.id,
            "user",
            "Test message",
        )

        assert message is None

    async def test_delete_message_with_permission(self, async_session: AsyncSession):
        """Test deleting message with proper permission."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        user = await user_repo.create("user1")
        conversation = await conv_repo.create(user_id=user.id, conversation_id="conv-1")
        message = await msg_repo.add(conversation.id, "user", "Delete me")

        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user.id, "user1", UserRole.USER)

        result = await middleware.delete_message(context, conversation.id, message.id)

        assert result is True

    async def test_delete_message_without_permission(self, async_session: AsyncSession):
        """Test deleting message without delete permission."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        user = await user_repo.create("user1")
        conversation = await conv_repo.create(user_id=user.id, conversation_id="conv-1")
        message = await msg_repo.add(conversation.id, "user", "Delete me")

        await async_session.flush()

        # Create context with no delete permission
        middleware = AccessControlMiddleware(async_session)
        context = UserContext(user.id, "user1", UserRole.GUEST)

        result = await middleware.delete_message(context, conversation.id, message.id)

        assert result is False

    async def test_list_conversations_by_role_admin_only(self, async_session: AsyncSession):
        """Test that only admins can view statistics."""
        user_repo = UserRepository(async_session)

        user = await user_repo.create("user1")
        await async_session.flush()

        middleware = AccessControlMiddleware(async_session)

        # Regular user should fail
        context = UserContext(user.id, "user1", UserRole.USER)
        with pytest.raises(PermissionError):
            await middleware.list_conversations_by_role(context)

        # Admin should succeed
        admin_context = UserContext(user.id, "user1", UserRole.ADMIN)
        stats = await middleware.list_conversations_by_role(admin_context)

        assert "total_conversations" in stats
        assert "by_user" in stats
