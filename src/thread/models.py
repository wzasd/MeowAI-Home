from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class Message:
    """单条消息"""
    role: str  # "user" | "assistant"
    content: str
    cat_id: Optional[str] = None  # 如果是猫回复，记录是哪只
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "cat_id": self.cat_id,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            cat_id=data.get("cat_id"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class Thread:
    """对话线程"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    current_cat_id: str = "orange"  # 默认使用阿橘
    is_archived: bool = False

    @classmethod
    def create(cls, name: str, current_cat_id: str = "orange") -> "Thread":
        """创建新 thread"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4())[:8],  # 短ID便于使用
            name=name,
            created_at=now,
            updated_at=now,
            current_cat_id=current_cat_id,
            messages=[]
        )

    def add_message(self, role: str, content: str, cat_id: Optional[str] = None):
        """添加消息并更新更新时间"""
        self.messages.append(Message(role=role, content=content, cat_id=cat_id))
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "current_cat_id": self.current_cat_id,
            "is_archived": self.is_archived
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Thread":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            current_cat_id=data.get("current_cat_id", "orange"),
            is_archived=data.get("is_archived", False)
        )
