from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Literal, Optional
import uuid

# 常量定义
DEFAULT_CAT_ID = "orange"
VALID_ROLES = ("user", "assistant")
RoleType = Literal["user", "assistant"]


@dataclass
class Message:
    """单条消息"""
    role: RoleType
    content: str
    cat_id: Optional[str] = None  # 如果是猫回复，记录是哪只
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    thinking: Optional[str] = None  # 思考过程（可选）
    is_internal: bool = False  # 是否是 A2A 内部对话
    parent_id: Optional[str] = None  # 关联的父消息ID（用于A2A链）
    metadata: Optional[dict] = None  # 附加元数据（如附件、richBlocks）

    def to_dict(self) -> dict:
        result = {
            "role": self.role,
            "content": self.content,
            "cat_id": self.cat_id,
            "timestamp": self.timestamp.isoformat()
        }
        if self.thinking:
            result["thinking"] = self.thinking
        if self.is_internal:
            result["is_internal"] = self.is_internal
        if self.parent_id:
            result["parent_id"] = self.parent_id
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        # 验证必填字段
        required = {"role", "content", "timestamp"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Message missing required fields: {missing}")

        # 验证 role 值
        role = data["role"]
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}, must be one of {VALID_ROLES}")

        return cls(
            role=role,
            content=data["content"],
            cat_id=data.get("cat_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            thinking=data.get("thinking"),
            is_internal=data.get("is_internal", False),
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata")
        )


@dataclass
class Thread:
    """对话线程"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    current_cat_id: str = DEFAULT_CAT_ID
    is_archived: bool = False
    project_path: str = ""  # 项目目录路径

    @classmethod
    def create(cls, name: str, current_cat_id: str = DEFAULT_CAT_ID, project_path: str = "") -> "Thread":
        """创建新 thread"""
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4())[:8],  # 短ID便于使用
            name=name,
            created_at=now,
            updated_at=now,
            current_cat_id=current_cat_id,
            messages=[],
            project_path=project_path or ""
        )

    def add_message(self, role: RoleType, content: str, cat_id: Optional[str] = None, metadata: Optional[dict] = None) -> None:
        """添加消息并更新更新时间"""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}, must be one of {VALID_ROLES}")
        self.messages.append(Message(role=role, content=content, cat_id=cat_id, metadata=metadata))
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "current_cat_id": self.current_cat_id,
            "is_archived": self.is_archived
        }
        if self.project_path:
            result["project_path"] = self.project_path
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Thread":
        # 验证必填字段
        required = {"id", "name", "created_at", "updated_at"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Thread missing required fields: {missing}")

        return cls(
            id=data["id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            current_cat_id=data.get("current_cat_id", DEFAULT_CAT_ID),
            is_archived=data.get("is_archived", False),
            project_path=data.get("project_path") or ""
        )
