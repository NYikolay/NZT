"""Tests for consolidation services — ConsolidationService and EmbeddingGeneratorService."""

from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.consolidation.services import ConsolidationService
from src.domain.consolidation.schemas import ConsolidationResult
from src.domain.extraction.schemas import (
    LLMExtractionResult,
    ExtractedEntitySchema,
    ExtractedEventSchema,
    ExtractedEntityRelation,
    ExtractedEntityRelationTypeSuggestion,
)
from src.domain.memory.models import (
    EntityTypes,
)
from src.domain.memory.schemas import (
    EntityResponse,
    EventResponse,
    RawMessageResponse,
)


# ---------------------------------------------------------------------------
# ConsolidationService tests
# ---------------------------------------------------------------------------


def _make_entity_schema(
    temp_id: int,
    name: str,
    entity_type: EntityTypes = EntityTypes.PERSON,
    events: list | None = None,
) -> ExtractedEntitySchema:
    return ExtractedEntitySchema(
        temp_id=temp_id,
        name=name,
        entity_type=entity_type,
        aliases=[],
        events=events or [],
    )


def _make_entity_response(
    temp_id: int,
    name: str,
    entity_type: EntityTypes = EntityTypes.PERSON,
    raw_message_id: int = 1,
) -> tuple[EntityResponse, UUID]:
    """Create a mock EntityResponse and return it along with a UUID."""
    entity_id = uuid4()
    resp = EntityResponse(
        id=entity_id,
        name=name,
        entity_type=entity_type,
        aliases=[],
        description=None,
        importance_score=0,
        raw_message_id=raw_message_id,
        user_id=uuid4(),
        created_at=MagicMock(),
        updated_at=MagicMock(),
        canonical_text=f"{entity_type.value}: {name}",
    )
    return resp, entity_id


class TestConsolidationServiceConsolidate:
    """Tests for ConsolidationService.consolidate — the main entry point."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def service(self, session, user_id):
        svc = ConsolidationService(session=session, user_id=user_id)
        return svc

    @pytest.fixture
    def raw_message_response(self, user_id):
        return RawMessageResponse(
            id=42,
            content="Test raw message",
            user_id=user_id,
            created_at=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_should_consolidate_full_flow(
        self, service, session, user_id, raw_message_response
    ):
        """consolidate should process entities, events, and relationships."""
        # ── Step 1: Mock raw message creation ──────────────────────
        service._raw_message_service.create_raw_message = AsyncMock(
            return_value=raw_message_response
        )

        # ── Step 2: Mock _consolidate_entities ─────────────────────
        entity_ids = [uuid4(), uuid4()]
        entity_responses = [
            EntityResponse(
                id=entity_ids[0],
                name="Alice",
                entity_type=EntityTypes.PERSON,
                aliases=[],
                description=None,
                importance_score=0,
                raw_message_id=raw_message_response.id,
                user_id=user_id,
                created_at=MagicMock(),
                updated_at=MagicMock(),
                canonical_text="PERSON: Alice",
            ),
            EntityResponse(
                id=entity_ids[1],
                name="AcmeCorp",
                entity_type=EntityTypes.ORGANIZATION,
                aliases=["Acme"],
                description=None,
                importance_score=0,
                raw_message_id=raw_message_response.id,
                user_id=user_id,
                created_at=MagicMock(),
                updated_at=MagicMock(),
                canonical_text="ORGANIZATION: AcmeCorp",
            ),
        ]
        service._consolidate_entities = AsyncMock(return_value=entity_responses)

        # ── Step 3: Mock consolidate_entities_events ──────────────
        event_ids = [uuid4(), uuid4()]
        event_responses = [
            EventResponse(
                id=event_ids[0],
                summary="Alice was hired",
                timestamp=None,
                importance_score=0,
                raw_message_id=raw_message_response.id,
                user_id=user_id,
                created_at=MagicMock(),
                updated_at=MagicMock(),
            ),
            EventResponse(
                id=event_ids[1],
                summary="Met at office",
                timestamp=None,
                importance_score=0,
                raw_message_id=raw_message_response.id,
                user_id=user_id,
                created_at=MagicMock(),
                updated_at=MagicMock(),
            ),
        ]
        service.consolidate_entities_events = AsyncMock(return_value=event_responses)

        # ── Step 4: Mock relationship bulk_create ──────────────────
        service._relationship_repo.bulk_create = AsyncMock()

        # ── Step 5: Mock relation type service ─────────────────────
        service._entity_rel_type_service.bulk_create_extracted_relation_types = (
            AsyncMock()
        )

        # ── Build extraction data ──────────────────────────────────
        extracted = LLMExtractionResult(
            entities=[
                _make_entity_schema(
                    temp_id=1,
                    name="Alice",
                    entity_type=EntityTypes.PERSON,
                    events=[
                        ExtractedEventSchema(summary="Alice was hired", timestamp=None),
                    ],
                ),
                _make_entity_schema(
                    temp_id=2,
                    name="AcmeCorp",
                    entity_type=EntityTypes.ORGANIZATION,
                    events=[
                        ExtractedEventSchema(summary="Met at office", timestamp=None),
                    ],
                ),
            ],
            related_entities=[
                ExtractedEntityRelation(
                    from_entity_temp_id=1,
                    to_entity_temp_id=2,
                    rel_type="WORKS_FOR",
                ),
            ],
            suggestions=[
                ExtractedEntityRelationTypeSuggestion(
                    name="NEW_TYPE",
                    description="A new type",
                    reasoning="LLM suggestion",
                ),
            ],
        )

        # ── Execute ────────────────────────────────────────────────
        result = await service.consolidate(
            extracted_data=extracted,
            raw_message="Test raw message",
        )

        # ── Assertions ─────────────────────────────────────────────
        assert isinstance(result, ConsolidationResult)
        assert result.raw_message.id == raw_message_response.id
        assert len(result.entities) == 2
        assert result.entities[0].name == "Alice"
        assert result.entities[1].name == "AcmeCorp"
        assert len(result.events) == 2

        # Verify raw message was created
        service._raw_message_service.create_raw_message.assert_awaited_once()

        # Verify relation type suggestions were created
        service._entity_rel_type_service.bulk_create_extracted_relation_types.assert_awaited_once()

        # Verify entities were consolidated
        service._consolidate_entities.assert_awaited_once()

        # Verify relationships were bulk-created
        service._relationship_repo.bulk_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_handle_empty_entities(
        self, service, session, user_id, raw_message_response
    ):
        """consolidate should work when no entities are extracted."""
        service._raw_message_service.create_raw_message = AsyncMock(
            return_value=raw_message_response
        )
        service._consolidate_entities = AsyncMock()
        service._event_repo.bulk_create = AsyncMock()
        service._relationship_repo.bulk_create = AsyncMock()
        service._entity_rel_type_service.bulk_create_extracted_relation_types = (
            AsyncMock()
        )

        extracted = LLMExtractionResult(
            entities=None,
            related_entities=None,
            suggestions=None,
        )

        result = await service.consolidate(
            extracted_data=extracted,
            raw_message="Empty message",
        )

        assert isinstance(result, ConsolidationResult)
        assert result.entities is None
        assert result.events is None
        service._consolidate_entities.assert_not_called()
        service._event_repo.bulk_create.assert_not_called()
        service._relationship_repo.bulk_create.assert_not_called()
        service._entity_rel_type_service.bulk_create_extracted_relation_types.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_handle_entities_without_events(
        self, service, session, user_id, raw_message_response
    ):
        """consolidate should create entities but skip events when none present."""
        entity_id = uuid4()
        entity_response = EntityResponse(
            id=entity_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=[],
            description=None,
            importance_score=0,
            raw_message_id=raw_message_response.id,
            user_id=user_id,
            created_at=MagicMock(),
            updated_at=MagicMock(),
            canonical_text="PERSON: Alice",
        )
        service._raw_message_service.create_raw_message = AsyncMock(
            return_value=raw_message_response
        )
        service._consolidate_entities = AsyncMock(return_value=[entity_response])
        service._event_repo.bulk_create = AsyncMock()
        service._relationship_repo.bulk_create = AsyncMock()
        service._entity_rel_type_service.bulk_create_extracted_relation_types = (
            AsyncMock()
        )

        extracted = LLMExtractionResult(
            entities=[
                _make_entity_schema(temp_id=1, name="Alice"),  # No events
            ],
            related_entities=None,
        )

        result = await service.consolidate(
            extracted_data=extracted,
            raw_message="No events",
        )

        assert len(result.entities) == 1
        assert result.events is None
        service._event_repo.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_skip_self_referencing_relationships(
        self, service, session, user_id, raw_message_response
    ):
        """consolidate should skip relationships where from == to."""
        entity_id = uuid4()
        entity_response = EntityResponse(
            id=entity_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=[],
            description=None,
            importance_score=0,
            raw_message_id=raw_message_response.id,
            user_id=user_id,
            created_at=MagicMock(),
            updated_at=MagicMock(),
            canonical_text="PERSON: Alice",
        )
        service._raw_message_service.create_raw_message = AsyncMock(
            return_value=raw_message_response
        )
        service._consolidate_entities = AsyncMock(return_value=[entity_response])
        service._relationship_repo.bulk_create = AsyncMock()
        service._entity_rel_type_service.bulk_create_extracted_relation_types = (
            AsyncMock()
        )

        extracted = LLMExtractionResult(
            entities=[
                _make_entity_schema(temp_id=1, name="Alice"),
            ],
            related_entities=[
                ExtractedEntityRelation(
                    from_entity_temp_id=1,
                    to_entity_temp_id=1,  # Self-referencing — should be skipped
                    rel_type="RELATES_TO",
                ),
            ],
        )

        await service.consolidate(
            extracted_data=extracted,
            raw_message="Self-reference",
        )

        # Should NOT be called because the only relationship was self-referencing
        service._relationship_repo.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_skip_relationships_with_missing_temp_ids(
        self, service, session, user_id, raw_message_response
    ):
        """consolidate should skip relationships where temp_id mapping is missing."""
        entity_id = uuid4()
        entity_response = EntityResponse(
            id=entity_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=[],
            description=None,
            importance_score=0,
            raw_message_id=raw_message_response.id,
            user_id=user_id,
            created_at=MagicMock(),
            updated_at=MagicMock(),
            canonical_text="PERSON: Alice",
        )
        service._raw_message_service.create_raw_message = AsyncMock(
            return_value=raw_message_response
        )
        service._consolidate_entities = AsyncMock(return_value=[entity_response])
        service._relationship_repo.bulk_create = AsyncMock()
        service._entity_rel_type_service.bulk_create_extracted_relation_types = (
            AsyncMock()
        )

        extracted = LLMExtractionResult(
            entities=[
                _make_entity_schema(temp_id=1, name="Alice"),
            ],
            related_entities=[
                ExtractedEntityRelation(
                    from_entity_temp_id=1,
                    to_entity_temp_id=999,  # Doesn't exist in mapping
                    rel_type="WORKS_FOR",
                ),
            ],
        )

        await service.consolidate(
            extracted_data=extracted,
            raw_message="Missing temp ID",
        )

        service._relationship_repo.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_map_temp_ids_to_uuids(
        self, service, session, user_id, raw_message_response
    ):
        """consolidate should correctly map temp_ids to actual entity UUIDs."""
        entity_ids = [uuid4(), uuid4()]
        entity_responses = [
            EntityResponse(
                id=entity_ids[0],
                name="Alice",
                entity_type=EntityTypes.PERSON,
                aliases=[],
                description=None,
                importance_score=0,
                raw_message_id=raw_message_response.id,
                user_id=user_id,
                created_at=MagicMock(),
                updated_at=MagicMock(),
                canonical_text="PERSON: Alice",
            ),
            EntityResponse(
                id=entity_ids[1],
                name="Bob",
                entity_type=EntityTypes.PERSON,
                aliases=[],
                description=None,
                importance_score=0,
                raw_message_id=raw_message_response.id,
                user_id=user_id,
                created_at=MagicMock(),
                updated_at=MagicMock(),
                canonical_text="PERSON: Bob",
            ),
        ]
        service._raw_message_service.create_raw_message = AsyncMock(
            return_value=raw_message_response
        )
        service._entity_rel_type_service.bulk_create_extracted_relation_types = (
            AsyncMock()
        )
        service._consolidate_entities = AsyncMock(return_value=entity_responses)
        service._relationship_repo.bulk_create = AsyncMock()

        extracted = LLMExtractionResult(
            entities=[
                _make_entity_schema(temp_id=1, name="Alice"),
                _make_entity_schema(temp_id=2, name="Bob"),
            ],
            related_entities=[
                ExtractedEntityRelation(
                    from_entity_temp_id=1,
                    to_entity_temp_id=2,
                    rel_type="FRIEND_OF",
                ),
            ],
        )

        await service.consolidate(
            extracted_data=extracted,
            raw_message="Temp ID mapping",
        )

        # Verify relationship was created with the correct UUIDs
        service._relationship_repo.bulk_create.assert_awaited_once()
        call_args = service._relationship_repo.bulk_create.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["from_entity_id"] == entity_ids[0]
        assert call_args[0]["to_entity_id"] == entity_ids[1]
        assert call_args[0]["rel_type"] == "FRIEND_OF"
