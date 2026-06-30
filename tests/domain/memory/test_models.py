"""Tests for memory domain models — construction, constraints, and enums."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.memory.models import (
    Entity,
    EntityTypes,
    Event,
    EventEntityRelation,
    RelationshipHistory,
    RawMessage,
    Embedding,
    EmbeddableType,
    EntityRelationType,
    EntityRelationTypeSuggestion,
    SuggestionStatus,
)


# ---------------------------------------------------------------------------
# Entity model tests
# ---------------------------------------------------------------------------


class TestEntityModel:
    """Tests for the Entity model."""

    def test_should_create_entity_with_minimal_fields(self):
        entity = Entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )
        assert entity.name == "Alice"
        assert entity.entity_type == EntityTypes.PERSON
        # aliases and importance_score have SQLAlchemy column defaults;
        # they are None until the object is added to a session
        assert entity.description is None

    def test_should_create_entity_with_all_fields(self):
        user_id = uuid4()
        entity = Entity(
            name="AcmeCorp",
            entity_type=EntityTypes.ORGANIZATION,
            aliases=["ACME", "Acme Inc."],
            description="A fictional corporation",
            importance_score=Decimal("50"),
            raw_message_id=42,
            user_id=user_id,
        )
        assert entity.name == "AcmeCorp"
        assert entity.entity_type == EntityTypes.ORGANIZATION
        assert entity.aliases == ["ACME", "Acme Inc."]
        assert entity.description == "A fictional corporation"
        assert entity.importance_score == Decimal("50")
        assert entity.raw_message_id == 42
        assert entity.user_id == user_id

    def test_should_have_entity_type_enum_values(self):
        assert EntityTypes.PERSON.value == "PERSON"
        assert EntityTypes.ORGANIZATION.value == "ORGANIZATION"
        assert EntityTypes.PROJECT.value == "PROJECT"
        assert EntityTypes.PRODUCT.value == "PRODUCT"
        assert EntityTypes.LOCATION.value == "LOCATION"
        assert EntityTypes.ASSET.value == "ASSET"
        assert EntityTypes.CONCEPT.value == "CONCEPT"
        assert EntityTypes.IDENTITY.value == "IDENTITY"
        assert EntityTypes.GOAL.value == "GOAL"

    def test_should_have_importance_check_constraint(self):
        for col_info in Entity.__table__.columns:
            if col_info.name == "importance_score":
                break
        # Verify the check constraint exists
        constraints = [
            c
            for c in Entity.__table__.constraints
            if hasattr(c, "sqltext") and "importance_score" in str(c.sqltext)
        ]
        assert len(constraints) >= 1

    def test_should_have_index_on_user_and_type(self):
        indexes = Entity.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "ix_entities_user_type" in index_names

    def test_should_have_index_on_name(self):
        indexes = Entity.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "ix_entities_name" in index_names

    def test_should_have_repr(self):
        entity = Entity(
            name="Bob",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )
        assert "Bob" in repr(entity)
        assert EntityTypes.PERSON.value in repr(entity)


# ---------------------------------------------------------------------------
# Event model tests
# ---------------------------------------------------------------------------


class TestEventModel:
    """Tests for the Event model."""

    def test_should_create_event_with_minimal_fields(self):
        event = Event(
            summary="Meeting with Alice",
            raw_message_id=1,
            user_id=uuid4(),
        )
        assert event.summary == "Meeting with Alice"
        assert event.timestamp is None
        # importance_score has a SQLAlchemy column default;
        # it is None until the object is added to a session

    def test_should_create_event_with_timestamp(self):
        ts = datetime.now(timezone.utc)
        event = Event(
            summary="Project deadline",
            timestamp=ts,
            importance_score=Decimal("85"),
            raw_message_id=2,
            user_id=uuid4(),
        )
        assert event.summary == "Project deadline"
        assert event.timestamp == ts
        assert event.importance_score == Decimal("85")

    def test_should_have_importance_check_constraint(self):
        constraints = [
            c
            for c in Event.__table__.constraints
            if hasattr(c, "sqltext") and "importance_score" in str(c.sqltext)
        ]
        assert len(constraints) >= 1

    def test_should_have_index_on_user_and_timestamp(self):
        index_names = {idx.name for idx in Event.__table__.indexes}
        assert "ix_events_user_timestamp" in index_names

    def test_should_have_repr(self):
        event = Event(summary="Test event", raw_message_id=1, user_id=uuid4())
        assert "Test event" in repr(event)


# ---------------------------------------------------------------------------
# EventEntityRelation model tests
# ---------------------------------------------------------------------------


class TestEventEntityRelationModel:
    """Tests for the EventEntityRelation model."""

    def test_should_create_relation(self):
        entity_id = uuid4()
        event_id = uuid4()
        rel = EventEntityRelation(entity_id=entity_id, event_id=event_id)
        assert rel.entity_id == entity_id
        assert rel.event_id == event_id
        # created_at has a SQLAlchemy column default;
        # it is None until the object is added to a session

    def test_should_have_composite_primary_key(self):
        pk_columns = {col.name for col in EventEntityRelation.__table__.primary_key}
        assert pk_columns == {"entity_id", "event_id"}

    def test_should_have_repr(self):
        rel = EventEntityRelation(entity_id=uuid4(), event_id=uuid4())
        assert "related to Event" in repr(rel)


# ---------------------------------------------------------------------------
# RelationshipHistory model tests
# ---------------------------------------------------------------------------


class TestRelationshipHistoryModel:
    """Tests for the RelationshipHistory model."""

    def test_should_create_relationship(self):
        from_id = uuid4()
        to_id = uuid4()
        rel = RelationshipHistory(
            from_entity_id=from_id,
            to_entity_id=to_id,
            rel_type="WORKS_FOR",
            user_id=uuid4(),
        )
        assert rel.from_entity_id == from_id
        assert rel.to_entity_id == to_id
        assert rel.rel_type == "WORKS_FOR"
        # valid_from has a SQLAlchemy column default;
        # it is None until the object is added to a session
        assert rel.valid_to is None

    def test_should_have_unique_constraint(self):
        unique_constraints = {
            tuple(sorted(c.columns.keys()))
            for c in RelationshipHistory.__table__.constraints
            if hasattr(c, "columns")
        }
        assert (
            "from_entity_id",
            "to_entity_id",
            "valid_from",
        ) in unique_constraints or any(
            "from_entity_id" in str(c)
            and "to_entity_id" in str(c)
            and "valid_from" in str(c)
            for c in RelationshipHistory.__table__.constraints
            if hasattr(c, "name") and c.name == "uq_relationship"
        )

    def test_should_have_no_self_relation_constraint(self):
        constraints = [
            c
            for c in RelationshipHistory.__table__.constraints
            if hasattr(c, "sqltext")
            and "from_entity_id != to_entity_id" in str(c.sqltext)
        ]
        assert len(constraints) >= 1

    def test_should_have_valid_period_constraint(self):
        constraints = [
            c
            for c in RelationshipHistory.__table__.constraints
            if hasattr(c, "sqltext") and "valid_to > valid_from" in str(c.sqltext)
        ]
        assert len(constraints) >= 1

    def test_should_have_indexes(self):
        index_names = {idx.name for idx in RelationshipHistory.__table__.indexes}
        assert "ix_valid_period" in index_names
        assert "ix_relationships_from_to" in index_names
        assert "ix_relationships_rel_type" in index_names

    def test_should_have_repr(self):
        rel = RelationshipHistory(
            from_entity_id=uuid4(),
            to_entity_id=uuid4(),
            rel_type="WORKS_FOR",
            user_id=uuid4(),
        )
        assert "Relationship" in repr(rel)
        assert "WORKS_FOR" in repr(rel)


# ---------------------------------------------------------------------------
# RawMessage model tests
# ---------------------------------------------------------------------------


class TestRawMessageModel:
    """Tests for the RawMessage model."""

    def test_should_create_raw_message(self):
        msg = RawMessage(content="Hello world", user_id=uuid4())
        assert msg.content == "Hello world"

    def test_should_have_repr(self):
        msg = RawMessage(content="Test", user_id=uuid4())
        assert "RawMessage" in repr(msg)


# ---------------------------------------------------------------------------
# Embedding model tests
# ---------------------------------------------------------------------------


class TestEmbeddingModel:
    """Tests for the Embedding model."""

    def test_should_create_embedding_with_uuid(self):
        emb = Embedding(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2, 0.3],
            model_version="text-embedding-3-small",
            model_provider="OpenAI",
            user_id=uuid4(),
        )
        assert emb.embeddable_uuid is not None
        assert emb.embeddable_id is None
        assert emb.embeddable_type == EmbeddableType.ENTITIES
        assert emb.model_version == "text-embedding-3-small"
        assert emb.model_provider == "OpenAI"

    def test_should_create_embedding_with_id(self):
        emb = Embedding(
            embeddable_id=42,
            embeddable_type=EmbeddableType.EVENTS,
            embedding=[0.4, 0.5, 0.6],
            model_version="text-embedding-3-large",
            model_provider="Cohere",
            user_id=uuid4(),
        )
        assert emb.embeddable_uuid is None
        assert emb.embeddable_id == 42
        assert emb.embeddable_type == EmbeddableType.EVENTS

    def test_should_create_embedding_with_chunks(self):
        emb = Embedding(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2],
            model_version="v1",
            model_provider="OpenAI",
            user_id=uuid4(),
            chunk_index=0,
            total_chunks=3,
        )
        assert emb.chunk_index == 0
        assert emb.total_chunks == 3

    def test_should_have_embeddable_type_enum_values(self):
        assert EmbeddableType.ENTITIES.value == "entities"
        assert EmbeddableType.EVENTS.value == "events"

    def test_should_have_exactly_one_id_constraint(self):
        constraint_names = {
            c.name for c in Embedding.__table__.constraints if hasattr(c, "name")
        }
        assert any("exactly_one_id" in name for name in constraint_names), (
            f"Expected constraint with 'exactly_one_id' not found. Available: {constraint_names}"
        )

    def test_should_have_vector_index(self):
        index_names = {idx.name for idx in Embedding.__table__.indexes}
        assert "ix_embeddings_vector" in index_names
        assert "ix_embeddings_lookup" in index_names
        assert "ix_embeddings_model" in index_names

    def test_should_validate_exclusive_fields(self):
        """Setting both embeddable_uuid and embeddable_id should raise."""
        emb = Embedding(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1],
            model_version="v1",
            model_provider="OpenAI",
            user_id=uuid4(),
        )
        with pytest.raises(ValueError, match="embeddable_uuid is already set"):
            emb.embeddable_id = 42

    def test_should_have_repr(self):
        emb = Embedding(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2],
            model_version="text-embedding-3-small",
            model_provider="OpenAI",
            user_id=uuid4(),
        )
        assert "Embedding" in repr(emb)
        assert "OpenAI" in repr(emb)


# ---------------------------------------------------------------------------
# EntityRelationType model tests
# ---------------------------------------------------------------------------


class TestEntityRelationTypeModel:
    """Tests for the EntityRelationType model."""

    def test_should_create_preset_type(self):
        rel_type = EntityRelationType(
            name="WORKS_FOR",
            description="Employment relationship",
            is_preset=True,
            is_accepted=True,
        )
        assert rel_type.name == "WORKS_FOR"
        assert rel_type.description == "Employment relationship"
        assert rel_type.is_preset is True
        assert rel_type.is_accepted is True

    def test_should_create_suggested_type(self):
        rel_type = EntityRelationType(
            name="COLLABORATES_WITH",
            is_preset=False,
            is_accepted=False,
        )
        assert rel_type.name == "COLLABORATES_WITH"
        assert rel_type.is_preset is False
        assert rel_type.is_accepted is False

    def test_should_have_unique_name(self):
        for col in EntityRelationType.__table__.columns:
            if col.name == "name":
                assert col.unique is True
                break

    def test_should_have_repr(self):
        rel_type = EntityRelationType(
            id=1, name="WORKS_FOR", is_preset=True, is_accepted=True
        )
        assert "WORKS_FOR" in repr(rel_type)
        assert "preset=True" in repr(rel_type) or "True" in repr(rel_type)


# ---------------------------------------------------------------------------
# EntityRelationTypeSuggestion model tests
# ---------------------------------------------------------------------------


class TestEntityRelationTypeSuggestionModel:
    """Tests for the EntityRelationTypeSuggestion model."""

    def test_should_create_suggestion(self):
        suggestion = EntityRelationTypeSuggestion(
            entity_relation_type_id=1,
            raw_message_id=42,
            user_id=uuid4(),
            reasoning="LLM thinks this is relevant",
        )
        assert suggestion.entity_relation_type_id == 1
        assert suggestion.raw_message_id == 42
        assert suggestion.reasoning == "LLM thinks this is relevant"
        # status has a SQLAlchemy column default;
        # it is None until the object is added to a session

    def test_should_create_suggestion_without_reasoning(self):
        suggestion = EntityRelationTypeSuggestion(
            entity_relation_type_id=2,
            raw_message_id=100,
            user_id=uuid4(),
        )
        assert suggestion.reasoning is None
        # status has a SQLAlchemy column default;
        # it is None until the object is added to a session

    def test_should_have_suggestion_status_enum_values(self):
        assert SuggestionStatus.PENDING.value == "pending"
        assert SuggestionStatus.ACCEPTED.value == "accepted"
        assert SuggestionStatus.REJECTED.value == "rejected"

    def test_should_have_index_on_user_and_status(self):
        index_names = {
            idx.name for idx in EntityRelationTypeSuggestion.__table__.indexes
        }
        assert "ix_entity_relation_type_suggestions_user_status" in index_names

    def test_should_have_repr(self):
        suggestion = EntityRelationTypeSuggestion(
            id=1,
            entity_relation_type_id=5,
            status=SuggestionStatus.PENDING,
            raw_message_id=42,
            user_id=uuid4(),
        )
        assert "Suggestion" in repr(suggestion)
        assert "PENDING" in repr(suggestion) or "pending" in repr(suggestion)
