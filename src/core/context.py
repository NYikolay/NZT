"""Centralized context variables for the application.

Use these ContextVars everywhere instead of declaring separate instances.
"""

from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="")
