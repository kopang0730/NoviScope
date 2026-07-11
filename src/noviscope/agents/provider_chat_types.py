from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user"]
    content: str
