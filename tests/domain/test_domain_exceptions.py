"""Tests for domain exceptions."""

from src.domain.exceptions import (
    BaseAppError,
    EntityNotFoundError,
    DuplicateEntityError,
    InvalidStateError,
)


class TestBaseAppError:
    def test_default_error_id_is_generated(self):
        """BaseAppError should auto-generate an error_id."""
        exc = BaseAppError(message="test")
        assert exc.error_id is not None
        assert len(exc.error_id) == 12  # uuid hex[:12]

    def test_error_id_can_be_provided(self):
        """BaseAppError should accept a custom error_id."""
        exc = BaseAppError(message="test", error_id="custom123")
        assert exc.error_id == "custom123"

    def test_message_and_description_defaults(self):
        """BaseAppError should have None message/description if not provided."""
        exc = BaseAppError()
        assert exc.message is None
        assert exc.description is None
        assert exc.error_code is None

    def test_str_representation(self):
        """str(exc) should return the message."""
        exc = BaseAppError(message="something went wrong")
        assert str(exc) == "something went wrong"

    def test_error_code_and_status(self):
        """BaseAppError should store error_code and status_code."""
        exc = BaseAppError(
            message="forbidden",
            error_code="FORBIDDEN",
            status_code=403,
        )
        assert exc.error_code == "FORBIDDEN"
        assert exc.status_code == 403


class TestEntityNotFoundError:
    def test_entity_not_found_defaults(self):
        """EntityNotFoundError should set 404 status."""
        exc = EntityNotFoundError(entity="User", entity_id=42)
        assert exc.status_code == 404
        assert exc.error_code == "USER_NOT_FOUND"
        assert "42" in exc.message
        assert exc.details["entity"] == "User"

    def test_entity_not_found_uuid(self):
        """EntityNotFoundError should handle UUID entity_id."""
        exc = EntityNotFoundError(
            entity="Event", entity_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert exc.status_code == 404
        assert "550e8400" in exc.message


class TestDuplicateEntityError:
    def test_duplicate_entity_defaults(self):
        """DuplicateEntityError should set 409 status."""
        exc = DuplicateEntityError(entity="User", field="email", value="test@test.com")
        assert exc.status_code == 409
        assert exc.error_code == "USER_ALREADY_EXISTS"
        assert "email" in exc.message
        assert exc.details["field"] == "email"


class TestInvalidStateError:
    def test_invalid_state_defaults(self):
        """InvalidStateError should set 409 status."""
        exc = InvalidStateError(message="Cannot transition to this state")
        assert exc.status_code == 409
        assert exc.error_code == "INVALID_STATE"

    def test_invalid_state_custom_error_code(self):
        """InvalidStateError should accept custom error_code."""
        exc = InvalidStateError(
            message="Entity is archived",
            error_code="ENTITY_ARCHIVED",
        )
        assert exc.error_code == "ENTITY_ARCHIVED"
