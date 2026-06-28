"""Services for the memory domain."""

from uuid import UUID

import structlog
from sqlalchemy import update

from src.domain.decorators import log_domain_operation
from src.domain.exceptions import EntityNotFoundError
from src.domain.memory.models import (
    EntityRelationType,
    EntityRelationTypeSuggestion,
    RelationshipHistory,
)
from src.domain.memory.repositories import EntityRelationTypeRepository

logger = structlog.get_logger()

DEFAULT_FALLBACK_TYPE_NAME = "RELATES_TO"


class EntityRelationTypeService:
    """Service for managing EntityRelationType lifecycle.

    Core flow for LLM interaction:
    1. LLM suggests a relation type name (e.g. "COLLABORATES_WITH")
    2. `get_or_create_relation_type()` finds or creates the type via repository
       - If type exists and is accepted → use it directly
       - If type exists but not accepted → store suggestion, return fallback
       - If type doesn't exist → create as unaccepted, store suggestion, return fallback
    3. `record_suggestion()` persists the LLM's reasoning and links to the message
    4. `resolve_and_create_relationship()` orchestrates the full flow:
       resolves the type, records a suggestion if needed, and creates the RelationshipHistory
    5. Admin reviews pending suggestions and accepts/rejects them later
    """

    def __init__(self, repo: EntityRelationTypeRepository | None = None):
        self._repo = repo or EntityRelationTypeRepository()

    @log_domain_operation("get_or_create_relation_type")
    async def get_or_create_relation_type(
        self,
        uow,
        name: str,
        description: str | None = None,
    ) -> EntityRelationType:
        """Find a relation type by name, or create it as unaccepted.

        If the type exists and is accepted → return it.
        If the type exists but is not accepted → return fallback.
        If the type doesn't exist → create as unaccepted, return fallback.

        The fallback type (RELATES_TO) must always exist for unaccepted suggestions.
        """
        existing = await self._repo.get_by_name(uow, name)

        if existing is not None and existing.is_accepted:
            return existing

        if existing is None:
            await self._repo.create_type(
                uow,
                name=name,
                description=description,
                is_preset=False,
                is_accepted=False,
            )

        return await self._get_fallback_type(uow)

    @log_domain_operation("record_suggestion")
    async def record_suggestion(
        self,
        uow,
        relation_type_id: int,
        raw_message_id: int,
        reasoning: str | None = None,
    ) -> EntityRelationTypeSuggestion:
        """Record an LLM suggestion for a relation type."""
        return await self._repo.create_suggestion(
            uow,
            entity_relation_type_id=relation_type_id,
            raw_message_id=raw_message_id,
            reasoning=reasoning,
        )

    @log_domain_operation("accept_relation_type")
    async def accept_relation_type(
        self,
        uow,
        type_id: int,
    ) -> EntityRelationType:
        """Mark a relation type as accepted.

        Once accepted, the type can be used directly in relationships.
        """
        rel_type = await self._repo.get_by_id(uow, type_id)

        if rel_type is None:
            raise EntityNotFoundError(entity="EntityRelationType", entity_id=type_id)

        rel_type.is_accepted = True

        # Also accept all pending suggestions for this type
        update_stmt = (
            update(EntityRelationTypeSuggestion)
            .where(
                EntityRelationTypeSuggestion.entity_relation_type_id == type_id,
                EntityRelationTypeSuggestion.status == "pending",
            )
            .values(status="accepted")
        )
        await uow.session.execute(update_stmt)

        return rel_type

    @log_domain_operation("reject_relation_type")
    async def reject_relation_type(
        self,
        uow,
        type_id: int,
    ) -> None:
        """Reject a relation type and all its pending suggestions."""
        rel_type = await self._repo.get_by_id(uow, type_id)

        if rel_type is None:
            raise EntityNotFoundError(entity="EntityRelationType", entity_id=type_id)

        # Mark all pending suggestions as rejected
        update_stmt = (
            update(EntityRelationTypeSuggestion)
            .where(
                EntityRelationTypeSuggestion.entity_relation_type_id == type_id,
                EntityRelationTypeSuggestion.status == "pending",
            )
            .values(status="rejected")
        )
        await uow.session.execute(update_stmt)

    @log_domain_operation("list_relation_types")
    async def list_relation_types(self, uow) -> list[EntityRelationType]:
        """Return all relation types."""
        return await self._repo.list_all(uow)

    @log_domain_operation("list_pending_suggestions")
    async def list_pending_suggestions(self, uow) -> list[EntityRelationTypeSuggestion]:
        """Return all pending (unreviewed) suggestions."""
        return await self._repo.get_pending_suggestions(uow)

    @log_domain_operation("resolve_and_create_relationship")
    async def resolve_and_create_relationship(
        self,
        uow,
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
        existing = await self._repo.get_by_name(uow, suggested_type_name)
        existing_type_id = existing.id if existing is not None else None

        # Step 2: Resolve the type
        resolved_type = await self.get_or_create_relation_type(
            uow=uow,
            name=suggested_type_name,
            description=description,
        )

        # Step 3: Record suggestion if the resolved type differs from what was suggested
        if raw_message_id is not None and type_name_upper != resolved_type.name:
            suggestion_type_id = existing_type_id or resolved_type.id
            await self.record_suggestion(
                uow=uow,
                relation_type_id=suggestion_type_id,
                raw_message_id=raw_message_id,
                reasoning=reasoning,
            )

        # Step 4: Create the relationship
        relationship = RelationshipHistory(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            rel_type=resolved_type.name,
            user_id=user_id,
        )
        uow.session.add(relationship)
        return relationship

    async def _get_fallback_type(self, uow) -> EntityRelationType:
        """Get the default fallback relation type.

        Raises EntityNotFoundError if fallback type doesn't exist.
        """
        fallback = await self._repo.get_by_name(uow, DEFAULT_FALLBACK_TYPE_NAME)

        if fallback is None or not fallback.is_accepted:
            raise EntityNotFoundError(
                entity="EntityRelationType",
                entity_id=DEFAULT_FALLBACK_TYPE_NAME,
            )

        return fallback
