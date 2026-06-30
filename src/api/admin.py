"""SQLAdmin admin panel setup.

Provides a web-based admin interface at /admin for managing all database models.
Authentication is handled via a simple username/password backed by env vars.
"""

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqladmin.widgets import BooleanInputWidget
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import settings
from src.domain.users.models import User, AuthIdentity, ConnectionChannel
from src.domain.memory.models import (
    Entity,
    Event,
    EventEntityRelation,
    RelationshipHistory,
    RawMessage,
    Embedding,
    EntityRelationType,
    EntityRelationTypeSuggestion,
)


# ---------------------------------------------------------------------------
# Authentication backend
# ---------------------------------------------------------------------------

if not hasattr(BooleanInputWidget, "validation_attrs"):
    BooleanInputWidget.validation_attrs = ["required"]


class AdminAuth(AuthenticationBackend):
    """Simple username/password auth for the admin panel.

    Credentials are read from environment variables ADMIN_USERNAME and
    ADMIN_PASSWORD.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        admin_user = getattr(settings, "ADMIN_USERNAME", "admin")
        admin_pass = getattr(settings, "ADMIN_PASSWORD", "admin")

        if username == admin_user and password == admin_pass:
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | bool:
        if request.session.get("authenticated"):
            return True
        return False


# ---------------------------------------------------------------------------
# Model view classes
# ---------------------------------------------------------------------------


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.username,
        User.first_name,
        User.role,
        User.is_active,
        User.created_at,
        User.updated_at,
    ]
    column_searchable_list = [User.username, User.first_name]
    column_sortable_list = [
        User.username,
        User.first_name,
        User.role,
        User.is_active,
        User.created_at,
    ]
    column_default_sort = [("created_at", True)]  # descending
    can_create = True
    can_edit = True
    can_delete = True
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"


class AuthIdentityAdmin(ModelView, model=AuthIdentity):
    column_list = [
        AuthIdentity.id,
        AuthIdentity.user_id,
        AuthIdentity.provider,
        AuthIdentity.provider_user_id,
        AuthIdentity.created_at,
    ]
    column_searchable_list = [AuthIdentity.provider, AuthIdentity.provider_user_id]
    column_sortable_list = [AuthIdentity.provider, AuthIdentity.created_at]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Auth Identity"
    name_plural = "Auth Identities"
    icon = "fa-solid fa-key"


class ConnectionChannelAdmin(ModelView, model=ConnectionChannel):
    column_list = [
        ConnectionChannel.id,
        ConnectionChannel.user_id,
        ConnectionChannel.channel,
        ConnectionChannel.first_seen_at,
        ConnectionChannel.last_seen_at,
    ]
    column_searchable_list = [ConnectionChannel.channel]
    column_sortable_list = [
        ConnectionChannel.channel,
        ConnectionChannel.first_seen_at,
        ConnectionChannel.last_seen_at,
    ]
    column_default_sort = [("last_seen_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Connection Channel"
    name_plural = "Connection Channels"
    icon = "fa-solid fa-plug"


class EntityAdmin(ModelView, model=Entity):
    column_list = [
        Entity.id,
        Entity.user_id,
        Entity.name,
        Entity.entity_type,
        Entity.importance_score,
        Entity.created_at,
        Entity.updated_at,
    ]
    column_searchable_list = [Entity.name, Entity.description]
    column_sortable_list = [
        Entity.name,
        Entity.entity_type,
        Entity.importance_score,
        Entity.created_at,
    ]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Entity"
    name_plural = "Entities"
    icon = "fa-solid fa-cube"


class EventAdmin(ModelView, model=Event):
    column_list = [
        Event.id,
        Event.user_id,
        Event.summary,
        Event.timestamp,
        Event.importance_score,
        Event.raw_message_id,
        Event.created_at,
    ]
    column_searchable_list = [Event.summary]
    column_sortable_list = [
        Event.timestamp,
        Event.importance_score,
        Event.created_at,
    ]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Event"
    name_plural = "Events"
    icon = "fa-solid fa-calendar"


class EventEntityRelationAdmin(ModelView, model=EventEntityRelation):
    column_list = [
        EventEntityRelation.entity_id,
        EventEntityRelation.event_id,
        EventEntityRelation.created_at,
    ]
    column_sortable_list = [EventEntityRelation.created_at]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Event-Entity Relation"
    name_plural = "Event-Entity Relations"
    icon = "fa-solid fa-link"


class RelationshipHistoryAdmin(ModelView, model=RelationshipHistory):
    column_list = [
        RelationshipHistory.id,
        RelationshipHistory.user_id,
        RelationshipHistory.from_entity_id,
        RelationshipHistory.to_entity_id,
        RelationshipHistory.rel_type,
        RelationshipHistory.valid_from,
        RelationshipHistory.valid_to,
        RelationshipHistory.created_at,
    ]
    column_searchable_list = [RelationshipHistory.rel_type]
    column_sortable_list = [
        RelationshipHistory.rel_type,
        RelationshipHistory.valid_from,
        RelationshipHistory.valid_to,
        RelationshipHistory.created_at,
    ]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Relationship History"
    name_plural = "Relationship Histories"
    icon = "fa-solid fa-arrows-left-right"


class RawMessageAdmin(ModelView, model=RawMessage):
    column_list = [
        RawMessage.id,
        RawMessage.user_id,
        RawMessage.content,
        RawMessage.created_at,
    ]
    column_searchable_list = [RawMessage.content]
    column_sortable_list = [RawMessage.created_at]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Raw Message"
    name_plural = "Raw Messages"
    icon = "fa-solid fa-message"


class EmbeddingAdmin(ModelView, model=Embedding):
    column_list = [
        Embedding.id,
        Embedding.user_id,
        Embedding.embeddable_type,
        Embedding.embeddable_uuid,
        Embedding.embeddable_id,
        Embedding.model_provider,
        Embedding.model_version,
        Embedding.chunk_index,
        Embedding.total_chunks,
        Embedding.created_at,
    ]
    column_searchable_list = [Embedding.model_provider, Embedding.model_version]
    column_sortable_list = [
        Embedding.embeddable_type,
        Embedding.model_provider,
        Embedding.created_at,
    ]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Embedding"
    name_plural = "Embeddings"
    icon = "fa-solid fa-vector-square"


class EntityRelationTypeAdmin(ModelView, model=EntityRelationType):
    column_list = [
        EntityRelationType.id,
        EntityRelationType.name,
        EntityRelationType.description,
        EntityRelationType.is_preset,
        EntityRelationType.is_accepted,
        EntityRelationType.created_at,
    ]
    column_searchable_list = [
        EntityRelationType.name,
        EntityRelationType.description,
    ]
    column_sortable_list = [
        EntityRelationType.name,
        EntityRelationType.is_preset,
        EntityRelationType.is_accepted,
        EntityRelationType.created_at,
    ]
    column_default_sort = [("name", False)]

    name = "Entity Relation Type"
    name_plural = "Entity Relation Types"
    icon = "fa-solid fa-tag"


class EntityRelationTypeSuggestionAdmin(ModelView, model=EntityRelationTypeSuggestion):
    column_list = [
        EntityRelationTypeSuggestion.id,
        EntityRelationTypeSuggestion.user_id,
        EntityRelationTypeSuggestion.entity_relation_type_id,
        EntityRelationTypeSuggestion.raw_message_id,
        EntityRelationTypeSuggestion.status,
        EntityRelationTypeSuggestion.created_at,
    ]
    column_searchable_list = [EntityRelationTypeSuggestion.reasoning]
    column_sortable_list = [
        EntityRelationTypeSuggestion.status,
        EntityRelationTypeSuggestion.created_at,
    ]
    column_default_sort = [("created_at", True)]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Relation Type Suggestion"
    name_plural = "Relation Type Suggestions"
    icon = "fa-solid fa-lightbulb"


# ---------------------------------------------------------------------------
# Setup function
# ---------------------------------------------------------------------------


def setup_admin(app, engine: AsyncEngine) -> Admin:
    """Create and mount the SQLAdmin instance on the given FastAPI app.

    Args:
        app: FastAPI application instance.
        engine: AsyncEngine for database access.

    Returns:
        The configured Admin instance.
    """
    auth_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        engine,
        title=f"{settings.PROJECT_TITLE} Admin",
        base_url="/admin",
        authentication_backend=auth_backend,
    )

    admin.add_view(UserAdmin)
    admin.add_view(AuthIdentityAdmin)
    admin.add_view(ConnectionChannelAdmin)
    admin.add_view(EntityAdmin)
    admin.add_view(EventAdmin)
    admin.add_view(EventEntityRelationAdmin)
    admin.add_view(RelationshipHistoryAdmin)
    admin.add_view(RawMessageAdmin)
    admin.add_view(EmbeddingAdmin)
    admin.add_view(EntityRelationTypeAdmin)
    admin.add_view(EntityRelationTypeSuggestionAdmin)

    return admin
