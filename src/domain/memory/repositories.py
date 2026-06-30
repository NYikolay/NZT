"""Repositories for the memory domain — data access with AGE graph sync."""

from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.memory.models import (
    Entity,
    Event,
    EventEntityRelation,
    RelationshipHistory,
    RawMessage,
    Embedding,
    EntityRelationType,
    EntityRelationTypeSuggestion,
    EntityTypes,
    EmbeddableType,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# EntityRepository
# ---------------------------------------------------------------------------


class EntityRepository:
    """Repository for Entity CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        name: str,
        entity_type: EntityTypes,
        aliases: list[str] | None = None,
        description: str | None = None,
        importance_score: int = 0,
        raw_message_id: int,
        user_id: UUID,
    ) -> Entity:
        entity = Entity(
            name=name,
            entity_type=entity_type,
            aliases=aliases or [],
            description=description,
            importance_score=importance_score,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get_by_id(self, entity_id: UUID) -> Entity | None:
        return await self.session.get(Entity, entity_id)

    async def get_by_name_and_user(self, name: str, user_id: UUID) -> Entity | None:
        stmt = select(Entity).where(
            and_(Entity.name == name, Entity.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_alias(self, alias: str, user_id: UUID) -> list[Entity]:
        """Find entities whose aliases array contains the given alias."""
        stmt = select(Entity).where(
            and_(
                Entity.user_id == user_id,
                Entity.aliases.any(alias),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: UUID,
        entity_type: EntityTypes | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Entity]:
        stmt = select(Entity).where(Entity.user_id == user_id)
        if entity_type is not None:
            stmt = stmt.where(Entity.entity_type == entity_type)
        stmt = stmt.order_by(Entity.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, entity: Entity, **fields) -> Entity:
        for key, value in fields.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self.session.flush()
        return entity


# ---------------------------------------------------------------------------
# EventRepository
# ---------------------------------------------------------------------------


class EventRepository:
    """Repository for Event CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        summary: str,
        timestamp: Optional[str | None] = None,
        importance_score: int = 0,
        raw_message_id: int,
        user_id: UUID,
    ) -> Event:
        event = Event(
            summary=summary,
            timestamp=timestamp,
            importance_score=importance_score,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_by_id(self, event_id: UUID) -> Event | None:
        return await self.session.get(Event, event_id)

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.user_id == user_id)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_entity(self, entity_id: UUID) -> list[Event]:
        stmt = (
            select(Event)
            .join(EventEntityRelation, EventEntityRelation.event_id == Event.id)
            .where(EventEntityRelation.entity_id == entity_id)
            .order_by(Event.timestamp.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def link_entity(self, event_id: UUID, entity_id: UUID) -> EventEntityRelation:
        relation = EventEntityRelation(
            event_id=event_id,
            entity_id=entity_id,
        )
        self.session.add(relation)
        await self.session.flush()
        return relation


# ---------------------------------------------------------------------------
# RelationshipHistoryRepository
# ---------------------------------------------------------------------------


class RelationshipHistoryRepository:
    """Repository for RelationshipHistory CRUD and queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        from_entity_id: UUID,
        to_entity_id: UUID,
        rel_type: str,
        user_id: UUID,
        valid_from=None,
        valid_to=None,
    ) -> RelationshipHistory:
        relationship = RelationshipHistory(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            rel_type=rel_type,
            user_id=user_id,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        self.session.add(relationship)
        return relationship

    async def find_by_entity(self, entity_id: UUID) -> list[RelationshipHistory]:
        """Find all relationships involving this entity (inbound + outbound)."""
        stmt = select(RelationshipHistory).where(
            or_(
                RelationshipHistory.from_entity_id == entity_id,
                RelationshipHistory.to_entity_id == entity_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_between(
        self, entity_a_id: UUID, entity_b_id: UUID
    ) -> list[RelationshipHistory]:
        """Find all relationships between two specific entities."""
        stmt = select(RelationshipHistory).where(
            or_(
                and_(
                    RelationshipHistory.from_entity_id == entity_a_id,
                    RelationshipHistory.to_entity_id == entity_b_id,
                ),
                and_(
                    RelationshipHistory.from_entity_id == entity_b_id,
                    RelationshipHistory.to_entity_id == entity_a_id,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# RawMessageRepository
# ---------------------------------------------------------------------------


class RawMessageRepository:
    """Repository for RawMessage CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, content: str, user_id: UUID) -> RawMessage:
        message = RawMessage(content=content, user_id=user_id)
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_by_id(self, message_id: int) -> RawMessage | None:
        return await self.session.get(RawMessage, message_id)

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RawMessage]:
        stmt = (
            select(RawMessage)
            .where(RawMessage.user_id == user_id)
            .order_by(RawMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# EmbeddingRepository
# ---------------------------------------------------------------------------


class EmbeddingRepository:
    """Repository for Embedding CRUD and vector search."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        embeddable_uuid: UUID | None = None,
        embeddable_id: int | None = None,
        embeddable_type: EmbeddableType,
        embedding: list[float],
        model_version: str,
        model_provider: str,
        user_id: UUID,
        chunk_index: int | None = None,
        total_chunks: int | None = None,
    ) -> Embedding:
        emb = Embedding(
            embeddable_uuid=embeddable_uuid,
            embeddable_id=embeddable_id,
            embeddable_type=embeddable_type,
            embedding=embedding,
            model_version=model_version,
            model_provider=model_provider,
            user_id=user_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
        )
        self.session.add(emb)
        await self.session.flush()
        return emb

    async def search_similar(
        self,
        *,
        query_vector: list[float],
        embeddable_type: EmbeddableType | None = None,
        user_id: UUID,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[tuple[Embedding, float]]:
        """Find similar embeddings using cosine distance.

        Returns a list of (Embedding, similarity_score) tuples ordered by
        most similar first.
        """
        distance = Embedding.embedding.cosine_distance(query_vector)
        similarity = 1 - distance

        stmt = (
            select(Embedding, similarity.label("similarity"))
            .where(
                and_(
                    Embedding.user_id == user_id,
                    distance < (1 - threshold),
                )
            )
            .order_by(distance)
            .limit(limit)
        )

        if embeddable_type is not None:
            stmt = stmt.where(Embedding.embeddable_type == embeddable_type)

        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def delete_by_embeddable(
        self,
        *,
        embeddable_uuid: UUID | None = None,
        embeddable_id: int | None = None,
    ) -> None:
        """Delete all embeddings for a given embeddable entity."""
        stmt = select(Embedding)
        if embeddable_uuid is not None:
            stmt = stmt.where(Embedding.embeddable_uuid == embeddable_uuid)
        if embeddable_id is not None:
            stmt = stmt.where(Embedding.embeddable_id == embeddable_id)

        result = await self.session.execute(stmt)
        for emb in result.scalars().all():
            await self.session.delete(emb)
        await self.session.flush()


# ---------------------------------------------------------------------------
# EntityRelationTypeRepository (existing, updated)
# ---------------------------------------------------------------------------


class EntityRelationTypeRepository:
    """Repository for EntityRelationType and Suggestion CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_type(
        self,
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
        self.session.add(t)
        await self.session.flush()
        return t

    async def get_by_name(self, name: str) -> EntityRelationType | None:
        stmt = select(EntityRelationType).where(EntityRelationType.name == name.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, type_id: int) -> EntityRelationType | None:
        return await self.session.get(EntityRelationType, type_id)

    async def list_all(self) -> list[EntityRelationType]:
        stmt = select(EntityRelationType).order_by(EntityRelationType.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_accepted_or_preset(self) -> list[EntityRelationType]:
        """Return relation types that are either accepted by the user or preset."""
        stmt = (
            select(EntityRelationType)
            .where(
                or_(
                    EntityRelationType.is_accepted,
                    EntityRelationType.is_preset,
                )
            )
            .order_by(EntityRelationType.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_suggestion(
        self,
        *,
        entity_relation_type_id: int,
        raw_message_id: int,
        user_id: UUID,
        reasoning: str | None = None,
        status: str = "pending",
    ) -> EntityRelationTypeSuggestion:
        s = EntityRelationTypeSuggestion(
            entity_relation_type_id=entity_relation_type_id,
            raw_message_id=raw_message_id,
            user_id=user_id,
            reasoning=reasoning,
            status=status,
        )
        self.session.add(s)
        await self.session.flush()
        return s

    async def get_pending_suggestions(self) -> list[EntityRelationTypeSuggestion]:
        stmt = (
            select(EntityRelationTypeSuggestion)
            .where(EntityRelationTypeSuggestion.status == "pending")
            .order_by(EntityRelationTypeSuggestion.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
