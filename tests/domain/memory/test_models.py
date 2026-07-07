"""Tests for memory domain models — constructors, properties, validation."""

from datetime import datetime, timezone
from uuid import uuid4
from decimal import Decimal

import pytest

from src.domain.memory.models import (
    Entity,
    EntityTypes,
    Event,
    EventEntityRelation,
    RelationshipHistory,
    RawMessage,
    RawMessageRoles,
    Embedding,
    EmbeddableType,
    EntityRelationType,
    EntityRelationTypeSuggestion,
)


class TestEntityModel:
    """Tests for Entity model construction and properties."""

    def test_should_construct_with_minimal_fields(self):
        """Entity should be constructable with required fields only."""
        entity = Entity(
            name="Test",
            entity_type=EntityTypes.PERSON,
            aliases=[],
            raw_message_id=1,
            user_id=uuid4(),
        )

        assert entity.name == "Test"
        assert entity.entity_type == EntityTypes.PERSON
        assert entity.aliases == []
        assert entity.description is None

    def test_should_construct_with_all_fields(self):
        """Entity should accept all optional fields."""
        user_id = uuid4()
        entity = Entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali", "A"],
            description="A person",
            importance_score=Decimal("50"),
            raw_message_id=1,
            user_id=user_id,
        )

        assert entity.name == "Alice"
        assert entity.aliases == ["Ali", "A"]
        assert entity.description == "A person"
        assert entity.importance_score == Decimal("50")

    def test_should_format_canonical_text_with_all_fields(self):
        """canonical_text should include type, name, aliases, and description."""
        entity = Entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],
            description="Main character",
            raw_message_id=1,
            user_id=uuid4(),
        )

        text = entity.canonical_text

        assert "PERSON: Alice" in text
        assert "Ali" in text
        assert "Main character" in text

    def test_should_format_canonical_text_without_description(self):
        """canonical_text should work without description."""
        entity = Entity(
            name="Bob",
            entity_type=EntityTypes.ORGANIZATION,
            aliases=[],
            raw_message_id=1,
            user_id=uuid4(),
        )

        text = entity.canonical_text

        assert "ORGANIZATION: Bob" in text
        assert "description" not in text.lower()

    def test_should_repr_entity(self):
        """__repr__ should include id, name, and type."""
        entity = Entity(
            name="Test",
            entity_type=EntityTypes.CONCEPT,
            aliases=[],
            raw_message_id=1,
            user_id=uuid4(),
        )

        rep = repr(entity)

        assert "Entity" in rep
        assert str(entity.id) in rep
        assert "Test" in rep
        assert "CONCEPT" in rep


class TestEventModel:
    """Tests for Event model construction."""

    def test_should_construct_with_minimal_fields(self):
        """Event should be constructable with required fields only."""
        event = Event(
            summary="Test event",
            importance_score=Decimal("0"),
            raw_message_id=1,
            user_id=uuid4(),
        )

        assert event.summary == "Test event"
        assert event.timestamp is None
        assert event.importance_score == Decimal("0")

    def test_should_construct_with_all_fields(self):
        """Event should accept all optional fields."""
        ts = datetime.now(timezone.utc)
        event = Event(
            summary="Important event",
            timestamp=ts,
            importance_score=Decimal("85"),
            raw_message_id=2,
            user_id=uuid4(),
        )

        assert event.summary == "Important event"
        assert event.timestamp == ts
        assert event.importance_score == Decimal("85")

    def test_should_repr_event(self):
        """__repr__ should include user_id and summary."""
        user_id = uuid4()
        event = Event(
            summary="Test event",
            importance_score=Decimal("0"),
            raw_message_id=1,
            user_id=user_id,
        )

        rep = repr(event)

        assert "Event" in rep
        assert str(user_id) in rep
        assert "Test event" in rep


class TestEventEntityRelationModel:
    """Tests for EventEntityRelation model."""

    def test_should_construct_with_required_fields(self):
        """EventEntityRelation should accept entity_id and event_id."""
        entity_id = uuid4()
        event_id = uuid4()

        rel = EventEntityRelation(entity_id=entity_id, event_id=event_id)

        assert rel.entity_id == entity_id
        assert rel.event_id == event_id

    def test_should_repr_event_entity_relation(self):
        """__repr__ should include entity and event IDs."""
        entity_id = uuid4()
        event_id = uuid4()
        rel = EventEntityRelation(entity_id=entity_id, event_id=event_id)

        rep = repr(rel)

        assert str(entity_id) in rep
        assert str(event_id) in rep


class TestRelationshipHistoryModel:
    """Tests for RelationshipHistory model construction."""

    def test_should_construct_with_required_fields(self):
        """RelationshipHistory should accept required fields."""
        from_id = uuid4()
        to_id = uuid4()
        user_id = uuid4()

        rel = RelationshipHistory(
            from_entity_id=from_id,
            to_entity_id=to_id,
            rel_type="WORKS_FOR",
            user_id=user_id,
        )

        assert rel.from_entity_id == from_id
        assert rel.to_entity_id == to_id
        assert rel.rel_type == "WORKS_FOR"
        assert rel.user_id == user_id
        assert rel.valid_to is None

    def test_should_repr_relationship(self):
        """__repr__ should include from, to, and type."""
        rel = RelationshipHistory(
            from_entity_id=uuid4(),
            to_entity_id=uuid4(),
            rel_type="FRIEND_OF",
            user_id=uuid4(),
        )

        rep = repr(rel)

        assert "FRIEND_OF" in rep
        assert "Relationship" in rep


class TestRawMessageModel:
    """Tests for RawMessage model construction."""

    def test_should_construct_with_user_role(self):
        """RawMessage should accept USER role."""
        msg = RawMessage(
            content="Hello",
            role=RawMessageRoles.USER,
            user_id=uuid4(),
        )

        assert msg.content == "Hello"
        assert msg.role == RawMessageRoles.USER

    def test_should_construct_with_assistant_role(self):
        """RawMessage should accept ASSISTANT role."""
        msg = RawMessage(
            content="AI response",
            role=RawMessageRoles.ASSISTANT,
            user_id=uuid4(),
        )

        assert msg.role == RawMessageRoles.ASSISTANT

    def test_should_repr_raw_message(self):
        """__repr__ should include id and user_id."""
        user_id = uuid4()
        msg = RawMessage(
            id=42, content="Test", role=RawMessageRoles.USER, user_id=user_id
        )

        rep = repr(msg)

        assert str(user_id) in rep
        assert "42" in rep


class TestEmbeddingModel:
    """Tests for Embedding model construction and validation."""

    def test_should_construct_with_embeddable_uuid(self):
        """Embedding should accept embeddable_uuid."""
        emb = Embedding(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2],
            model_version="v1",
            model_provider="openai",
            user_id=uuid4(),
        )

        assert emb.embeddable_uuid is not None
        assert emb.embeddable_id is None
        assert emb.embeddable_type == EmbeddableType.ENTITIES

    def test_should_construct_with_embeddable_id(self):
        """Embedding should accept embeddable_id."""
        emb = Embedding(
            embeddable_id=42,
            embeddable_type=EmbeddableType.RAW_MESSAGE,
            embedding=[0.3],
            model_version="v2",
            model_provider="cohere",
            user_id=uuid4(),
        )

        assert emb.embeddable_id == 42
        assert emb.embeddable_uuid is None

    def test_should_raise_when_both_ids_set(self):
        """validate_exclusive_fields should raise when both IDs are set."""
        with pytest.raises(ValueError, match="embeddable_uuid is already set"):
            emb = Embedding(
                embeddable_uuid=uuid4(),
                embeddable_type=EmbeddableType.ENTITIES,
                embedding=[0.1],
                model_version="v1",
                model_provider="p",
                user_id=uuid4(),
            )
            # Setting embeddable_id should trigger the validator
            emb.embeddable_id = 42  # noqa

    def test_should_construct_with_chunk_info(self):
        """Embedding should accept chunk_index and total_chunks."""
        emb = Embedding(
            embeddable_id=1,
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1],
            model_version="v1",
            model_provider="p",
            user_id=uuid4(),
            chunk_index=0,
            total_chunks=3,
        )

        assert emb.chunk_index == 0
        assert emb.total_chunks == 3

    def test_should_repr_embedding(self):
        """__repr__ should include type, id, and model info."""
        emb = Embedding(
            embeddable_id=42,
            embeddable_type=EmbeddableType.RAW_MESSAGE,
            embedding=[0.1],
            model_version="text-embedding-3-small",
            model_provider="openai",
            user_id=uuid4(),
        )

        rep = repr(emb)

        assert "RAW_MESSAGE" in rep
        assert "openai" in rep
        assert "text-embedding-3-small" in rep


class TestEntityRelationTypeModel:
    """Tests for EntityRelationType model construction."""

    def test_should_construct_with_required_fields(self):
        """EntityRelationType should accept name."""
        rt = EntityRelationType(name="WORKS_FOR")

        assert rt.name == "WORKS_FOR"
        assert rt.description is None

    def test_should_construct_with_all_fields(self):
        """EntityRelationType should accept all optional fields."""
        rt = EntityRelationType(
            name="FRIEND_OF",
            description="A friendship relation",
            is_preset=True,
            is_accepted=True,
        )

        assert rt.name == "FRIEND_OF"
        assert rt.description == "A friendship relation"
        assert rt.is_preset is True
        assert rt.is_accepted is True

    def test_should_repr_entity_relation_type(self):
        """__repr__ should include id, name, preset, and accepted."""
        rt = EntityRelationType(
            id=5, name="WORKS_FOR", is_preset=True, is_accepted=False
        )

        rep = repr(rt)

        assert "5" in rep
        assert "WORKS_FOR" in rep
        assert "preset=True" in rep
        assert "accepted=False" in rep


class TestEntityRelationTypeSuggestionModel:
    """Tests for EntityRelationTypeSuggestion model construction."""

    def test_should_construct_with_required_fields(self):
        """EntityRelationTypeSuggestion should accept required fields."""
        suggestion = EntityRelationTypeSuggestion(
            entity_relation_type_id=1,
            raw_message_id=42,
            user_id=uuid4(),
        )

        assert suggestion.entity_relation_type_id == 1
        assert suggestion.raw_message_id == 42
        assert suggestion.reasoning is None

    def test_should_construct_with_reasoning(self):
        """EntityRelationTypeSuggestion should accept reasoning."""
        suggestion = EntityRelationTypeSuggestion(
            entity_relation_type_id=2,
            raw_message_id=100,
            user_id=uuid4(),
            reasoning="LLM thinks this is relevant",
        )

        assert suggestion.reasoning == "LLM thinks this is relevant"

    def test_should_repr_suggestion(self):
        """__repr__ should include id, type_id, and status."""
        suggestion = EntityRelationTypeSuggestion(
            id=10,
            entity_relation_type_id=3,
            raw_message_id=50,
            user_id=uuid4(),
        )

        rep = repr(suggestion)

        assert "10" in rep
        assert "3" in rep
