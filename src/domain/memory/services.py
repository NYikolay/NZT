"""Services for the memory domain."""

from typing import Literal, List
from uuid import UUID

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.decorators import log_domain_operation
from src.domain.exceptions import EntityNotFoundError
from src.domain.extraction.schemas import ExtractedEntityRelationTypeSuggestion
from src.domain.memory.models import (
    Entity,
    Event,
    EventEntityRelation,
    EntityRelationType,
    EntityRelationTypeSuggestion,
    RelationshipHistory,
    EntityTypes,
    SuggestionStatus,
    RawMessageRoles,
)
from src.domain.memory.repositories import (
    EntityRepository,
    EventRepository,
    RelationshipHistoryRepository,
    EntityRelationTypeRepository,
    RawMessageRepository,
)
from src.domain.memory.schemas import (
    EntityRelationTypeCreate,
    EntityRelationTypeSuggestionCreate,
    RawMessageResponse,
)

logger = structlog.get_logger()

DEFAULT_FALLBACK_TYPE_NAME = "RELATES_TO"


# ---------------------------------------------------------------------------
# EntityService
# ---------------------------------------------------------------------------


class RawMessageService:
    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self._repo = RawMessageRepository(session=session)
        self._user_id = user_id

    @log_domain_operation("create_raw_message")
    async def create_raw_message(
        self, content: str, role: RawMessageRoles
    ) -> RawMessageResponse:
        raw_message_model = await self._repo.create(
            content=content, user_id=self._user_id, role=role
        )

        return RawMessageResponse.model_validate(raw_message_model)


class EntityService:
    """Service for Entity lifecycle management.

    Handles creation, updates, and merging of duplicate entities.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repo = EntityRepository(session=session)

    @log_domain_operation("get_or_create_entity")
    async def get_or_create_entity(
        self,
        *,
        name: str,
        entity_type: EntityTypes,
        aliases: list[str] | None = None,
        description: str | None = None,
        importance_score: int = 0,
        raw_message_id: int,
        user_id: UUID,
    ) -> tuple[Entity, Literal["created", "already_exists"]]:
        """Get an existing entity by name for this user, or create a new one.

        If an entity with the same canonical name already exists for the
        user, its aliases are merged (new aliases appended) and the entity
        is returned with status "already_exists".
        """
        existing = await self._repo.get_by_name_and_user(name, user_id)

        if existing is not None:
            # Merge new aliases into existing entity
            new_aliases = aliases or []
            current_aliases = existing.aliases or []
            merged_aliases = list(set(current_aliases + new_aliases))
            if merged_aliases != current_aliases:
                await self._repo.update(existing, aliases=merged_aliases)

            # Update description if not already set
            if description and not existing.description:
                await self._repo.update(existing, description=description)

            logger.info(
                "entity_already_exists",
                entity_id=str(existing.id),
                name=name,
                user_id=str(user_id),
            )
            return existing, "already_exists"

        entity = await self._repo.create(
            name=name,
            entity_type=entity_type,
            aliases=aliases,
            description=description,
            importance_score=importance_score,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )

        logger.info(
            "entity_created",
            entity_id=str(entity.id),
            name=name,
            entity_type=entity_type.value,
            user_id=str(user_id),
        )
        return entity, "created"

    @log_domain_operation("update_entity")
    async def update_entity(self, entity_id: UUID, **fields) -> Entity:
        """Update an entity's fields. Raises EntityNotFoundError if missing."""
        entity = await self._repo.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError(entity="Entity", entity_id=entity_id)

        return await self._repo.update(entity, **fields)

    @log_domain_operation("merge_entities")
    async def merge_entities(self, keep_id: UUID, merge_id: UUID) -> Entity:
        """Merge a duplicate entity into the kept entity.

        All relationships and event links are transferred to the kept
        entity, and the merged entity is deleted.
        """
        keep = await self._repo.get_by_id(keep_id)
        merge = await self._repo.get_by_id(merge_id)

        if keep is None:
            raise EntityNotFoundError(entity="Entity", entity_id=keep_id)
        if merge is None:
            raise EntityNotFoundError(entity="Entity", entity_id=merge_id)

        # Merge aliases
        keep_aliases = set(keep.aliases or [])
        merge_aliases = set(merge.aliases or [])
        if merge_aliases - keep_aliases:
            await self._repo.update(keep, aliases=list(keep_aliases | merge_aliases))

        # Delete the merged entity
        await self.session.delete(merge)

        logger.info(
            "entities_merged",
            keep_id=str(keep_id),
            merge_id=str(merge_id),
        )
        return keep


# ---------------------------------------------------------------------------
# EventService
# ---------------------------------------------------------------------------


class EventService:
    """Service for Event lifecycle management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repo = EventRepository(session)

    @log_domain_operation("create_event")
    async def create_event(
        self,
        *,
        summary: str,
        timestamp: str | None = None,
        importance_score: int = 0,
        raw_message_id: int,
        entity_ids: list[UUID] | None = None,
        user_id: UUID,
    ) -> Event:
        """Create an event and optionally link it to entities.

        Args:
            summary: Brief description of the event.
            timestamp: When the event occurred (ISO string or None).
            importance_score: Event importance (0, 25, 50, 70, 85, 95, 99).
            raw_message_id: The message that produced this event.
            entity_ids: Optional list of entity UUIDs to link to this event.
            user_id: The user who owns this event.

        Returns:
            The newly created Event model.
        """
        event = await self._repo.create(
            summary=summary,
            timestamp=timestamp,
            importance_score=importance_score,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )

        if entity_ids:
            for entity_id in entity_ids:
                await self._repo.link_entity(event_id=event.id, entity_id=entity_id)

        logger.info(
            "event_created",
            event_id=str(event.id),
            summary=summary[:80],
            linked_entities=len(entity_ids) if entity_ids else 0,
            user_id=str(user_id),
        )
        return event

    @log_domain_operation("link_entity_to_event")
    async def link_entity_to_event(
        self, event_id: UUID, entity_id: UUID
    ) -> EventEntityRelation:
        """Link an existing entity to an existing event."""
        return await self._repo.link_entity(event_id=event_id, entity_id=entity_id)


# ---------------------------------------------------------------------------
# EntityRelationTypeService (existing, updated)
# ---------------------------------------------------------------------------


class EntityRelationTypeService:
    """Service for managing EntityRelationType lifecycle.

    Core flow for LLM interaction:
    1. LLM suggests a relation type name (e.g. "COLLABORATES_WITH")
    2. ``get_or_create_relation_type()`` finds or creates the type via repository
       - If type exists and is accepted → use it directly
       - If type exists but not accepted → store suggestion, return fallback
       - If type doesn't exist → create as unaccepted, store suggestion, return fallback
    3. ``record_suggestion()`` persists the LLM's reasoning and links to the message
    4. ``resolve_and_create_relationship()`` orchestrates the full flow:
       resolves the type, records a suggestion if needed, and creates the RelationshipHistory
    5. Admin reviews pending suggestions and accepts/rejects them later
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repo = EntityRelationTypeRepository(session=session)
        self._relationship_repo = RelationshipHistoryRepository(session=session)

    @log_domain_operation("get_or_create_relation_type")
    async def get_or_create_relation_type(
        self,
        name: str,
        description: str | None = None,
    ) -> EntityRelationType:
        """Find a relation type by name, or create it as unaccepted.

        If the type exists and is accepted → return it.
        If the type exists but is not accepted → return fallback.
        If the type doesn't exist → create as unaccepted, return fallback.

        The fallback type (RELATES_TO) must always exist for unaccepted suggestions.
        """
        existing = await self._repo.get_by_name(name)

        if existing is not None and existing.is_accepted:
            return existing

        if existing is None:
            await self._repo.create_type(
                name=name,
                description=description,
                is_preset=False,
                is_accepted=False,
            )

        return await self._get_fallback_type()

    @log_domain_operation("bulk_create_extracted_relation_types")
    async def bulk_create_extracted_relation_types(
        self,
        suggested_rel_types: List[ExtractedEntityRelationTypeSuggestion],
        source_message_id: int,
    ):
        rel_types_to_insert = [
            EntityRelationTypeCreate(
                name=ext_rel_type.name, description=ext_rel_type.description
            ).model_dump()
            for ext_rel_type in suggested_rel_types
        ]

        created_rel_types = await self._repo.bulk_create_types(rel_types_to_insert)
        rel_types_by_name = {rel.name: rel for rel in created_rel_types}

        suggestions_to_insert = [
            EntityRelationTypeSuggestionCreate(
                entity_relation_type_id=rel_type.id,
                raw_message_id=source_message_id,
                reasoning=suggestion.reasoning,
            ).model_dump()
            for suggestion in suggested_rel_types
            if (rel_type := rel_types_by_name.get(suggestion.name)) is not None
        ]

        await self._repo.bulk_create_suggestions(suggestions_to_insert)

    @log_domain_operation("record_suggestion")
    async def record_suggestion(
        self,
        relation_type_id: int,
        raw_message_id: int,
        user_id: UUID,
        reasoning: str | None = None,
    ) -> EntityRelationTypeSuggestion:
        """Record an LLM suggestion for a relation type."""
        return await self._repo.create_suggestion(
            entity_relation_type_id=relation_type_id,
            raw_message_id=raw_message_id,
            user_id=user_id,
            reasoning=reasoning,
        )

    @log_domain_operation("accept_relation_type")
    async def accept_relation_type(
        self,
        type_id: int,
    ) -> EntityRelationType:
        """Mark a relation type as accepted.

        Once accepted, the type can be used directly in relationships.
        """
        rel_type = await self._repo.get_by_id(type_id)

        if rel_type is None:
            raise EntityNotFoundError(entity="EntityRelationType", entity_id=type_id)

        rel_type.is_accepted = True

        # Also accept all pending suggestions for this type
        update_stmt = (
            update(EntityRelationTypeSuggestion)
            .where(
                EntityRelationTypeSuggestion.entity_relation_type_id == type_id,
                EntityRelationTypeSuggestion.status == SuggestionStatus.PENDING,
            )
            .values(status=SuggestionStatus.ACCEPTED)
        )
        await self.session.execute(update_stmt)

        return rel_type

    @log_domain_operation("reject_relation_type")
    async def reject_relation_type(
        self,
        type_id: int,
    ) -> None:
        """Reject a relation type and all its pending suggestions."""
        rel_type = await self._repo.get_by_id(type_id)

        if rel_type is None:
            raise EntityNotFoundError(entity="EntityRelationType", entity_id=type_id)

        # Mark all pending suggestions as rejected
        update_stmt = (
            update(EntityRelationTypeSuggestion)
            .where(
                EntityRelationTypeSuggestion.entity_relation_type_id == type_id,
                EntityRelationTypeSuggestion.status == SuggestionStatus.PENDING,
            )
            .values(status=SuggestionStatus.REJECTED)
        )
        await self.session.execute(update_stmt)

    @log_domain_operation("list_relation_types")
    async def list_relation_types(self) -> list[EntityRelationType]:
        """Return all relation types."""
        return await self._repo.list_all()

    @log_domain_operation("list_pending_suggestions")
    async def list_pending_suggestions(self) -> list[EntityRelationTypeSuggestion]:
        """Return all pending (unreviewed) suggestions."""
        return await self._repo.get_pending_suggestions()

    @log_domain_operation("resolve_and_create_relationship")
    async def resolve_and_create_relationship(
        self,
        from_entity_id: UUID,
        to_entity_id: UUID,
        suggested_type_name: str,
        user_id: UUID,
        raw_message_id: int | None = None,
        reasoning: str | None = None,
        description: str | None = None,
    ) -> RelationshipHistory:
        """Full flow: resolve LLM-suggested type → record suggestion → create RelationshipHistory.

        This is the main entry point for the extraction pipeline when LLM
        identifies a relationship between two entities.
        """
        type_name_upper = suggested_type_name.upper()

        # Step 1: Check if the suggested type already exists
        existing = await self._repo.get_by_name(suggested_type_name)
        existing_type_id = existing.id if existing is not None else None

        # Step 2: Resolve the type
        resolved_type = await self.get_or_create_relation_type(
            name=suggested_type_name,
            description=description,
        )

        # Step 3: Record suggestion if the resolved type differs from what was suggested
        if raw_message_id is not None and type_name_upper != resolved_type.name:
            suggestion_type_id = existing_type_id or resolved_type.id
            await self.record_suggestion(
                relation_type_id=suggestion_type_id,
                raw_message_id=raw_message_id,
                user_id=user_id,
                reasoning=reasoning,
            )

        # Step 4: Create the relationship via the RelationshipHistoryRepository
        relationship = await self._relationship_repo.create(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            rel_type=resolved_type.name,
            user_id=user_id,
        )
        return relationship

    async def _get_fallback_type(self) -> EntityRelationType:
        """Get the default fallback relation type.

        Raises EntityNotFoundError if fallback type doesn't exist.
        """
        fallback = await self._repo.get_by_name(DEFAULT_FALLBACK_TYPE_NAME)

        if fallback is None or not fallback.is_accepted:
            raise EntityNotFoundError(
                entity="EntityRelationType",
                entity_id=DEFAULT_FALLBACK_TYPE_NAME,
            )

        return fallback
