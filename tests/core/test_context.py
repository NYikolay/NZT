"""Tests for the centralized ContextVars."""

from src.core.context import request_id_var, user_id_var, client_ip_var


class TestContextVars:
    def test_request_id_default(self):
        """request_id_var should default to empty string."""
        assert request_id_var.get() == ""

    def test_user_id_default(self):
        """user_id_var should default to empty string."""
        assert user_id_var.get() == ""

    def test_client_ip_default(self):
        """client_ip_var should default to empty string."""
        assert client_ip_var.get() == ""

    def test_set_and_get_request_id(self):
        """Setting a ContextVar should be readable within the same context."""
        token = request_id_var.set("req-123")
        assert request_id_var.get() == "req-123"
        request_id_var.reset(token)
        assert request_id_var.get() == ""

    def test_set_and_get_user_id(self):
        token = user_id_var.set("user-42")
        assert user_id_var.get() == "user-42"
        user_id_var.reset(token)

    def test_set_and_get_client_ip(self):
        token = client_ip_var.set("192.168.1.1")
        assert client_ip_var.get() == "192.168.1.1"
        client_ip_var.reset(token)
