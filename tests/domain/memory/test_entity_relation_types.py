"""Tests for EntityRelationType management (models + services)."""

from uuid import UUID, uuid4
from unittest.mock import AsyncMock

import pytest

from src.domain.memory.models import (
    EntityRelationType,
    EntityRelationTypeSuggestion,
    RelationshipHistory,
    SuggestionStatus,
)
from src.domain.memory.services import EntityRelationTypeService
from src.domain.exceptions import EntityNotFoundError


# ---------------------------------------------------------------------------
# Service tests — EntityRelationTypeService
# ---------------------------------------------------------------------------

# The service is constructed with a session; it creates _repo and _relationship_repo internally.
# We test by patching the internal repos with mocks.


class TestGetOrCreateRelationType:
    """get_or_create_relation_type — core logic for LLM interaction."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityRelationTypeService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_return_accepted_type_when_it_exists(
        self, service, mock_session
    ):
        """When a type exists and is accepted, return it directly."""
        accepted = EntityRelationType(id=1, name="WORKS_FOR", is_accepted=True)
        service._repo.get_by_name = AsyncMock(return_value=accepted)

        result = await service.get_or_create_relation_type(name="WORKS_FOR")

        assert result.id == 1
        assert result.name == "WORKS_FOR"
        assert result.is_accepted is True
        service._repo.get_by_name.assert_awaited_once_with("WORKS_FOR")

    @pytest.mark.asyncio
    async def test_should_return_fallback_when_type_not_accepted(
        self, service, mock_session
    ):
        """When a type exists but is not accepted, return the fallback."""
        unaccepted = EntityRelationType(
            id=2, name="COLLABORATES_WITH", is_accepted=False
        )
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)

        service._repo.get_by_name = AsyncMock(side_effect=[unaccepted, fallback])

        result = await service.get_or_create_relation_type(name="COLLABORATES_WITH")

        assert result.id == 99
        assert result.name == "RELATES_TO"
        assert service._repo.get_by_name.call_count == 2

    @pytest.mark.asyncio
    async def test_should_create_new_type_and_return_fallback(
        self, service, mock_session
    ):
        """When a type doesn't exist, create it and return fallback."""
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)

        service._repo.get_by_name = AsyncMock(side_effect=[None, fallback])
        service._repo.create_type = AsyncMock(
            return_value=EntityRelationType(id=3, name="NEW_TYPE", is_accepted=False)
        )

        result = await service.get_or_create_relation_type(
            name="NEW_TYPE", description="A new type"
        )

        assert result.id == 99
        assert result.name == "RELATES_TO"
        service._repo.create_type.assert_awaited_once_with(
            name="NEW_TYPE",
            description="A new type",
            is_preset=False,
            is_accepted=False,
        )

    @pytest.mark.asyncio
    async def test_should_raise_when_no_fallback(self, service, mock_session):
        """If the fallback type is missing, raise an error."""
        service._repo.get_by_name = AsyncMock(side_effect=[None, None])

        with pytest.raises(EntityNotFoundError):
            await service.get_or_create_relation_type(name="NEW_TYPE")

    @pytest.mark.asyncio
    async def test_should_not_create_duplicate_type(self, service, mock_session):
        """If a type already exists (even if unaccepted), don't create a duplicate."""
        existing = EntityRelationType(id=2, name="COLLABORATES_WITH", is_accepted=False)
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)

        service._repo.get_by_name = AsyncMock(side_effect=[existing, fallback])
        # Mock create_type to track calls
        service._repo.create_type = AsyncMock()

        result = await service.get_or_create_relation_type(name="COLLABORATES_WITH")

        assert result.name == "RELATES_TO"
        service._repo.create_type.assert_not_called()


class TestRecordSuggestion:
    """Tests for recording LLM suggestions."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityRelationTypeService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_record_suggestion_with_reasoning(self, service, mock_session):
        """A suggestion should be stored with LLM reasoning."""
        expected = EntityRelationTypeSuggestion(
            id=1,
            entity_relation_type_id=2,
            raw_message_id=42,
            user_id=uuid4(),
            reasoning="test",
            status=SuggestionStatus.PENDING,
        )
        service._repo.create_suggestion = AsyncMock(return_value=expected)

        result = await service.record_suggestion(
            relation_type_id=2,
            raw_message_id=42,
            user_id=expected.user_id,
            reasoning="test",
        )

        assert result.reasoning == "test"
        assert result.status == SuggestionStatus.PENDING
        service._repo.create_suggestion.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_suggestion_without_reasoning(
        self, service, mock_session
    ):
        """A suggestion can be created without reasoning."""
        expected = EntityRelationTypeSuggestion(
            id=1,
            entity_relation_type_id=3,
            raw_message_id=100,
            user_id=uuid4(),
            reasoning=None,
            status=SuggestionStatus.PENDING,
        )
        service._repo.create_suggestion = AsyncMock(return_value=expected)

        result = await service.record_suggestion(
            relation_type_id=3,
            raw_message_id=100,
            user_id=expected.user_id,
        )

        assert result.reasoning is None
        assert result.status == SuggestionStatus.PENDING


class TestAcceptRejectRelationType:
    """Tests for accepting/rejecting suggested relation types."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityRelationTypeService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_accept_a_suggested_type(self, service, mock_session):
        """Marking a type as accepted should update its status."""
        rel_type = EntityRelationType(id=5, name="COLLABORATES_WITH", is_accepted=False)
        service._repo.get_by_id = AsyncMock(return_value=rel_type)
        mock_session.execute = AsyncMock()

        result = await service.accept_relation_type(type_id=5)

        assert result.is_accepted is True
        service._repo.get_by_id.assert_awaited_once_with(5)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_reject_a_suggested_type(self, service, mock_session):
        """Marking suggestions as rejected should update their status."""
        rel_type = EntityRelationType(id=5, name="COLLABORATES_WITH")
        service._repo.get_by_id = AsyncMock(return_value=rel_type)
        mock_session.execute = AsyncMock()

        await service.reject_relation_type(type_id=5)

        service._repo.get_by_id.assert_awaited_once_with(5)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_raise_when_accepting_nonexistent(self, service, mock_session):
        """Accepting a non-existent type should raise."""
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.accept_relation_type(type_id=999)

    @pytest.mark.asyncio
    async def test_should_raise_when_rejecting_nonexistent(self, service, mock_session):
        """Rejecting a non-existent type should raise."""
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.reject_relation_type(type_id=999)


class TestListOperations:
    """Tests for listing relation types and suggestions."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityRelationTypeService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_list_all_relation_types(self, service, mock_session):
        """Should return all relation types."""
        types = [
            EntityRelationType(id=1, name="WORKS_FOR"),
            EntityRelationType(id=2, name="RELATES_TO"),
        ]
        service._repo.list_all = AsyncMock(return_value=types)

        result = await service.list_relation_types()

        assert len(result) == 2
        service._repo.list_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_list_pending_suggestions(self, service, mock_session):
        """Should return pending suggestions."""
        suggestions = [
            EntityRelationTypeSuggestion(
                id=1,
                entity_relation_type_id=5,
                raw_message_id=42,
                user_id=uuid4(),
                status=SuggestionStatus.PENDING,
            ),
        ]
        service._repo.get_pending_suggestions = AsyncMock(return_value=suggestions)

        result = await service.list_pending_suggestions()

        assert len(result) == 1
        assert result[0].status == SuggestionStatus.PENDING
        service._repo.get_pending_suggestions.assert_awaited_once()


class TestResolveAndCreateRelationship:
    """Tests for the full flow: resolve type → record suggestion → create relationship."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityRelationTypeService(session=mock_session)

    @pytest.fixture
    def from_entity_id(self) -> UUID:
        return uuid4()

    @pytest.fixture
    def to_entity_id(self) -> UUID:
        return uuid4()

    @pytest.fixture
    def user_id(self) -> UUID:
        return uuid4()

    @pytest.mark.asyncio
    async def test_should_create_relationship_with_accepted_type(
        self, service, mock_session, from_entity_id, to_entity_id, user_id
    ):
        """When the suggested type is accepted, use it directly."""
        accepted = EntityRelationType(id=1, name="WORKS_FOR", is_accepted=True)
        service._repo.get_by_name = AsyncMock(return_value=accepted)
        service._relationship_repo.create = AsyncMock(
            return_value=RelationshipHistory(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                rel_type="WORKS_FOR",
                user_id=user_id,
            )
        )

        result = await service.resolve_and_create_relationship(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="WORKS_FOR",
            user_id=user_id,
        )

        assert isinstance(result, RelationshipHistory)
        assert result.rel_type == "WORKS_FOR"
        assert result.from_entity_id == from_entity_id
        assert result.to_entity_id == to_entity_id

    @pytest.mark.asyncio
    async def test_should_use_fallback_and_record_suggestion(
        self, service, mock_session, from_entity_id, to_entity_id, user_id
    ):
        """When the suggested type is new, use fallback and record suggestion."""
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)
        service._repo.get_by_name = AsyncMock(side_effect=[None, fallback])
        service._repo.create_type = AsyncMock()
        service._repo.create_suggestion = AsyncMock()
        service._relationship_repo.create = AsyncMock(
            return_value=RelationshipHistory(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                rel_type="RELATES_TO",
                user_id=user_id,
            )
        )

        result = await service.resolve_and_create_relationship(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="CUSTOM_NEW_TYPE",
            user_id=user_id,
            raw_message_id=42,
            reasoning="LLM thinks this is a custom relationship",
        )

        assert result.rel_type == "RELATES_TO"
        service._repo.create_suggestion.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_not_record_suggestion_without_raw_message_id(
        self, service, mock_session, from_entity_id, to_entity_id, user_id
    ):
        """If no raw_message_id, skip suggestion recording."""
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)
        service._repo.get_by_name = AsyncMock(side_effect=[None, fallback])
        service._repo.create_type = AsyncMock()
        # Mock create_suggestion to track calls
        service._repo.create_suggestion = AsyncMock()
        service._relationship_repo.create = AsyncMock(
            return_value=RelationshipHistory(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                rel_type="RELATES_TO",
                user_id=user_id,
            )
        )

        result = await service.resolve_and_create_relationship(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="NEW_TYPE",
            user_id=user_id,
        )

        assert result.rel_type == "RELATES_TO"
        service._repo.create_suggestion.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_record_suggestion_for_existing_unaccepted(
        self, service, mock_session, from_entity_id, to_entity_id, user_id
    ):
        """When suggesting an existing unaccepted type, record suggestion linked to it."""
        unaccepted = EntityRelationType(id=5, name="PENDING_TYPE", is_accepted=False)
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)
        service._repo.get_by_name = AsyncMock(side_effect=[unaccepted, fallback])
        service._repo.create_suggestion = AsyncMock()
        service._relationship_repo.create = AsyncMock(
            return_value=RelationshipHistory(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                rel_type="RELATES_TO",
                user_id=user_id,
            )
        )

        result = await service.resolve_and_create_relationship(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="PENDING_TYPE",
            user_id=user_id,
            raw_message_id=7,
        )

        assert result.rel_type == "RELATES_TO"
        service._repo.create_suggestion.assert_awaited_once()
