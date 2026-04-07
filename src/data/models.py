from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
import uuid


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    role: Role
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Thread:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now()
