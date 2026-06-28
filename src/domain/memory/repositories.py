"""Repositories for the memory domain — data access with AGE graph sync."""

import structlog
from sqlalchemy import select

from src.domain.memory.models import (
    EntityRelationType,
    EntityRelationTypeSuggestion,
)

logger = structlog.get_logger()


class EntityRelationTypeRepository:
    """Repository for EntityRelationType and Suggestion CRUD."""

    async def create_type(
        self,
        uow,
        *,
        name: str,
        description: str | None = None,
        is_preset: bool = False,
        is_accepted: bool = False,
    ) -> EntityRelationType:
        t = EntityRelationType(
            name=name,
            description=description,
            is_preset=is_preset,
            is_accepted=is_accepted,
        )
        uow.session.add(t)
        await uow.session.flush()
        return t

    async def get_by_name(self, uow, name: str) -> EntityRelationType | None:
        stmt = select(EntityRelationType).where(EntityRelationType.name == name.upper())
        result = await uow.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, uow, type_id: int) -> EntityRelationType | None:
        return await uow.session.get(EntityRelationType, type_id)

    async def list_all(self, uow) -> list[EntityRelationType]:
        stmt = select(EntityRelationType).order_by(EntityRelationType.name)
        result = await uow.session.execute(stmt)
        return list(result.scalars().all())

    async def create_suggestion(
        self,
        uow,
        *,
        entity_relation_type_id: int,
        raw_message_id: int,
        reasoning: str | None = None,
        status: str = "pending",
    ) -> EntityRelationTypeSuggestion:
        s = EntityRelationTypeSuggestion(
            entity_relation_type_id=entity_relation_type_id,
            raw_message_id=raw_message_id,
            reasoning=reasoning,
            status=status,
        )
        uow.session.add(s)
        await uow.session.flush()
        return s

    async def get_pending_suggestions(self, uow) -> list[EntityRelationTypeSuggestion]:
        stmt = (
            select(EntityRelationTypeSuggestion)
            .where(EntityRelationTypeSuggestion.status == "pending")
            .order_by(EntityRelationTypeSuggestion.created_at.desc())
        )
        result = await uow.session.execute(stmt)
        return list(result.scalars().all())
