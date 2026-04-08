import json
from pathlib import Path
from typing import Dict
from src.thread.models import Thread


DEFAULT_STORAGE_PATH = Path.home() / ".meowai" / "threads.json"


class ThreadPersistence:
    """Thread JSON 持久化"""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._ensure_dir()

    def _ensure_dir(self):
        """确保存储目录存在"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, threads: Dict[str, Thread], current_thread_id: str = None) -> None:
        """保存所有 threads 到 JSON"""
        data = {
            "version": 1,
            "current_thread_id": current_thread_id,
            "threads": {tid: t.to_dict() for tid, t in threads.items()}
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> tuple[Dict[str, Thread], str]:
        """从 JSON 加载所有 threads 和当前 thread ID"""
        if not self.storage_path.exists():
            return {}, None

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            threads = {}
            for tid, tdata in data.get("threads", {}).items():
                threads[tid] = Thread.from_dict(tdata)
            current_id = data.get("current_thread_id")
            return threads, current_id
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 文件损坏，返回空
            print(f"Warning: Failed to load threads: {e}")
            return {}, None

    def exists(self) -> bool:
        """检查存储文件是否存在"""
        return self.storage_path.exists()
