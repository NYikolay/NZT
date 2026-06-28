"""Tests for EntityRelationType management (models + services)."""

from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.memory.models import (
    EntityRelationType,
    EntityRelationTypeSuggestion,
    RelationshipHistory,
)
from src.domain.memory.services import EntityRelationTypeService
from src.domain.exceptions import EntityNotFoundError


# ---------------------------------------------------------------------------
# EntityRelationType model tests
# ---------------------------------------------------------------------------


class TestEntityRelationTypeModel:
    """Tests for the EntityRelationType model."""

    def test_should_create_preset_relation_type(self):
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

    def test_should_create_llm_suggested_type(self):
        rel_type = EntityRelationType(
            name="COLLABORATES_WITH",
            description="Collaboration between entities",
            is_preset=False,
            is_accepted=False,
        )
        assert rel_type.name == "COLLABORATES_WITH"
        assert rel_type.is_accepted is False
        assert rel_type.is_preset is False

    def test_should_default_to_not_preset_and_not_accepted(self):
        rel_type = EntityRelationType(name="CUSTOM_TYPE")
        assert rel_type.name == "CUSTOM_TYPE"
        assert rel_type.is_preset is None or rel_type.is_preset is False
        assert rel_type.is_accepted is None or rel_type.is_accepted is False

    def test_should_have_unique_name_constraint(self):
        for col_info in EntityRelationType.__table__.columns:
            if col_info.name == "name":
                assert col_info.unique is True
                break


# ---------------------------------------------------------------------------
# Service tests — using mocked repository
# ---------------------------------------------------------------------------


class TestGetOrCreateRelationType:
    """get_or_create_relation_type — core logic for LLM interaction."""

    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo):
        return EntityRelationTypeService(repo=mock_repo)

    @pytest.mark.asyncio
    async def test_should_return_accepted_type_when_it_exists(self, service, mock_repo):
        """When a type exists and is accepted, return it directly."""
        accepted = EntityRelationType(id=1, name="WORKS_FOR", is_accepted=True)
        mock_repo.get_by_name = AsyncMock(return_value=accepted)

        result = await service.get_or_create_relation_type(
            uow=MagicMock(), name="WORKS_FOR"
        )

        assert result.id == 1
        assert result.name == "WORKS_FOR"
        assert result.is_accepted is True
        mock_repo.get_by_name.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_return_fallback_when_type_not_accepted(
        self, service, mock_repo
    ):
        """When a type exists but is not accepted, return the fallback."""
        unaccepted = EntityRelationType(
            id=2, name="COLLABORATES_WITH", is_accepted=False
        )
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)

        mock_repo.get_by_name = AsyncMock(side_effect=[unaccepted, fallback])

        result = await service.get_or_create_relation_type(
            uow=MagicMock(), name="COLLABORATES_WITH"
        )

        assert result.id == 99
        assert result.name == "RELATES_TO"
        assert mock_repo.get_by_name.await_count == 2

    @pytest.mark.asyncio
    async def test_should_create_new_type_and_return_fallback(self, service, mock_repo):
        """When a type doesn't exist, create it and return fallback."""
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)

        mock_repo.get_by_name = AsyncMock(side_effect=[None, fallback])
        mock_repo.create_type = AsyncMock()

        result = await service.get_or_create_relation_type(
            uow=MagicMock(), name="NEW_TYPE", description="A new type"
        )

        assert result.id == 99
        assert result.name == "RELATES_TO"
        mock_repo.create_type.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_raise_when_no_fallback(self, service, mock_repo):
        """If the fallback type is missing, raise an error."""
        mock_repo.get_by_name = AsyncMock(side_effect=[None, None])

        with pytest.raises(EntityNotFoundError):
            await service.get_or_create_relation_type(uow=MagicMock(), name="NEW_TYPE")

    @pytest.mark.asyncio
    async def test_should_not_create_duplicate_type(self, service, mock_repo):
        """If a type already exists (even if unaccepted), don't create a duplicate."""
        existing = EntityRelationType(id=2, name="COLLABORATES_WITH", is_accepted=False)
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)

        mock_repo.get_by_name = AsyncMock(side_effect=[existing, fallback])

        result = await service.get_or_create_relation_type(
            uow=MagicMock(), name="COLLABORATES_WITH"
        )

        assert result.name == "RELATES_TO"
        mock_repo.create_type.assert_not_called()


class TestRecordSuggestion:
    """Tests for recording LLM suggestions."""

    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo):
        return EntityRelationTypeService(repo=mock_repo)

    @pytest.mark.asyncio
    async def test_should_record_suggestion_with_reasoning(self, service, mock_repo):
        """A suggestion should be stored with LLM reasoning."""
        expected = EntityRelationTypeSuggestion(
            id=1,
            entity_relation_type_id=2,
            raw_message_id=42,
            reasoning="test",
            status="pending",
        )
        mock_repo.create_suggestion = AsyncMock(return_value=expected)

        result = await service.record_suggestion(
            uow=MagicMock(), relation_type_id=2, raw_message_id=42, reasoning="test"
        )

        assert result.reasoning == "test"
        assert result.status == "pending"
        mock_repo.create_suggestion.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_suggestion_without_reasoning(self, service, mock_repo):
        """A suggestion can be created without reasoning."""
        expected = EntityRelationTypeSuggestion(
            id=1,
            entity_relation_type_id=3,
            raw_message_id=100,
            reasoning=None,
            status="pending",
        )
        mock_repo.create_suggestion = AsyncMock(return_value=expected)

        result = await service.record_suggestion(
            uow=MagicMock(), relation_type_id=3, raw_message_id=100
        )

        assert result.reasoning is None
        assert result.status == "pending"


class TestAcceptRejectRelationType:
    """Tests for accepting/rejecting suggested relation types."""

    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo):
        return EntityRelationTypeService(repo=mock_repo)

    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.session = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_should_accept_a_suggested_type(self, service, mock_repo, mock_uow):
        """Marking a type as accepted should update its status."""
        rel_type = EntityRelationType(id=5, name="COLLABORATES_WITH", is_accepted=False)
        mock_repo.get_by_id = AsyncMock(return_value=rel_type)
        mock_uow.session.execute = AsyncMock()

        result = await service.accept_relation_type(uow=mock_uow, type_id=5)

        assert result.is_accepted is True
        mock_repo.get_by_id.assert_awaited_once_with(mock_uow, 5)

    @pytest.mark.asyncio
    async def test_should_reject_a_suggested_type(self, service, mock_repo, mock_uow):
        """Marking suggestions as rejected should update their status."""
        rel_type = EntityRelationType(id=5, name="COLLABORATES_WITH")
        mock_repo.get_by_id = AsyncMock(return_value=rel_type)
        mock_uow.session.execute = AsyncMock()

        await service.reject_relation_type(uow=mock_uow, type_id=5)

        mock_repo.get_by_id.assert_awaited_once_with(mock_uow, 5)

    @pytest.mark.asyncio
    async def test_should_raise_when_accepting_nonexistent(
        self, service, mock_repo, mock_uow
    ):
        """Accepting a non-existent type should raise."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.accept_relation_type(uow=mock_uow, type_id=999)

    @pytest.mark.asyncio
    async def test_should_raise_when_rejecting_nonexistent(
        self, service, mock_repo, mock_uow
    ):
        """Rejecting a non-existent type should raise."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.reject_relation_type(uow=mock_uow, type_id=999)


class TestListOperations:
    """Tests for listing relation types and suggestions."""

    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo):
        return EntityRelationTypeService(repo=mock_repo)

    @pytest.mark.asyncio
    async def test_should_list_all_relation_types(self, service, mock_repo):
        """Should return all relation types."""
        types = [
            EntityRelationType(id=1, name="WORKS_FOR"),
            EntityRelationType(id=2, name="RELATES_TO"),
        ]
        mock_repo.list_all = AsyncMock(return_value=types)

        result = await service.list_relation_types(uow=MagicMock())

        assert len(result) == 2
        mock_repo.list_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_list_pending_suggestions(self, service, mock_repo):
        """Should return pending suggestions."""
        suggestions = [MagicMock(status="pending"), MagicMock(status="pending")]
        mock_repo.get_pending_suggestions = AsyncMock(return_value=suggestions)

        result = await service.list_pending_suggestions(uow=MagicMock())

        assert len(result) == 2
        mock_repo.get_pending_suggestions.assert_awaited_once()


class TestResolveAndCreateRelationship:
    """Tests for the full flow: resolve type → record suggestion → create relationship."""

    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo):
        return EntityRelationTypeService(repo=mock_repo)

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
        self, service, mock_repo, from_entity_id, to_entity_id, user_id
    ):
        """When the suggested type is accepted, use it directly."""
        accepted = EntityRelationType(id=1, name="WORKS_FOR", is_accepted=True)
        mock_repo.get_by_name = AsyncMock(return_value=accepted)

        result = await service.resolve_and_create_relationship(
            uow=MagicMock(),
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
        self, service, mock_repo, from_entity_id, to_entity_id, user_id
    ):
        """When the suggested type is new, use fallback and record suggestion."""
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)
        mock_repo.get_by_name = AsyncMock(side_effect=[None, fallback])
        mock_repo.create_type = AsyncMock()
        mock_repo.create_suggestion = AsyncMock()

        result = await service.resolve_and_create_relationship(
            uow=MagicMock(),
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="CUSTOM_NEW_TYPE",
            user_id=user_id,
            raw_message_id=42,
            reasoning="LLM thinks this is a custom relationship",
        )

        assert result.rel_type == "RELATES_TO"
        mock_repo.create_suggestion.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_not_record_suggestion_without_raw_message_id(
        self, service, mock_repo, from_entity_id, to_entity_id, user_id
    ):
        """If no raw_message_id, skip suggestion recording."""
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)
        mock_repo.get_by_name = AsyncMock(side_effect=[None, fallback])
        mock_repo.create_type = AsyncMock()

        result = await service.resolve_and_create_relationship(
            uow=MagicMock(),
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="NEW_TYPE",
            user_id=user_id,
        )

        assert result.rel_type == "RELATES_TO"
        mock_repo.create_suggestion.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_record_suggestion_for_existing_unaccepted(
        self, service, mock_repo, from_entity_id, to_entity_id, user_id
    ):
        """When suggesting an existing unaccepted type, record suggestion linked to it."""
        unaccepted = EntityRelationType(id=5, name="PENDING_TYPE", is_accepted=False)
        fallback = EntityRelationType(id=99, name="RELATES_TO", is_accepted=True)
        mock_repo.get_by_name = AsyncMock(side_effect=[unaccepted, fallback])
        mock_repo.create_suggestion = AsyncMock()

        result = await service.resolve_and_create_relationship(
            uow=MagicMock(),
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            suggested_type_name="PENDING_TYPE",
            user_id=user_id,
            raw_message_id=7,
        )

        assert result.rel_type == "RELATES_TO"
        mock_repo.create_suggestion.assert_awaited_once()
