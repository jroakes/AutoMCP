"""Minimal mock of FastMCP-specific classes needed for tests."""


class Message:
    """Base message class for mock."""

    def __init__(self, content):
        self.content = content


class UserMessage(Message):
    """Mock of UserMessage from fastmcp."""

    def __init__(self, content):
        super().__init__(content)
        self.role = "user"


class AssistantMessage(Message):
    """Mock of AssistantMessage from fastmcp."""

    def __init__(self, content):
        super().__init__(content)
        self.role = "assistant"
