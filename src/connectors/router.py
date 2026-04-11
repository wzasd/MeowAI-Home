"""ConnectorRouter — message processing pipeline.

Pipeline: Dedup → Group Whitelist → Command Intercept → Media Process →
          Binding Lookup → @Mention Parse → Store → Broadcast → Invoke
"""
import asyncio
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import (
    IConnector,
    IInboundAdapter,
    IOutboundAdapter,
    InboundMessage,
    OutboundMessage,
    MessageType,
)


class ConnectorRouter:
    """Message processing router for all connectors.

    Implements the full pipeline:
    1. Deduplication (URL-based)
    2. Group whitelist
    3. Command interception
    4. Media processing
    5. Binding lookup
    6. @mention parsing
    7. Store to thread
    8. Broadcast to listeners
    9. Invoke cat
    """

    def __init__(self):
        self._adapters: Dict[str, Any] = {}
        self._command_handlers: Dict[str, Callable] = {}
        self._message_handlers: List[Callable] = []
        self._recent_messages: Set[str] = set()  # For dedup
        self._dedup_window_seconds: int = 300  # 5 min dedup window
        self._whitelisted_groups: Optional[Set[str]] = None
        self._thread_manager: Optional[Any] = None
        self._invocation_queue: Optional[Any] = None
        self._cat_registry: Optional[Any] = None

    def register_adapter(self, name: str, adapter: Any) -> None:
        """Register a connector adapter."""
        self._adapters[name] = adapter
        if hasattr(adapter, "set_message_handler"):
            adapter.set_message_handler(self._on_inbound_message)

    def unregister_adapter(self, name: str) -> None:
        """Unregister an adapter."""
        if name in self._adapters:
            del self._adapters[name]

    def register_command(self, command: str, handler: Callable) -> None:
        """Register a command handler.

        Handler signature: async handler(message: InboundMessage) -> bool
        """
        self._command_handlers[command] = handler

    def register_message_handler(self, handler: Callable) -> None:
        """Register a general message handler."""
        self._message_handlers.append(handler)

    def set_thread_manager(self, thread_manager: Any) -> None:
        """Set thread manager for persistence."""
        self._thread_manager = thread_manager

    def set_invocation_queue(self, queue: Any) -> None:
        """Set invocation queue for cat dispatch."""
        self._invocation_queue = queue

    def set_cat_registry(self, registry: Any) -> None:
        """Set cat registry for mention resolution."""
        self._cat_registry = registry

    def set_whitelisted_groups(self, groups: Set[str]) -> None:
        """Set whitelisted group IDs."""
        self._whitelisted_groups = groups

    def _generate_message_key(self, adapter: str, message: InboundMessage) -> str:
        """Generate unique key for message dedup."""
        return f"{adapter}:{message.message_id}"

    def _is_duplicate(self, key: str) -> bool:
        """Check if message is duplicate."""
        if key in self._recent_messages:
            return True
        self._recent_messages.add(key)
        # Clean old entries periodically (simplified)
        if len(self._recent_messages) > 1000:
            self._recent_messages.clear()
        return False

    def parse_mentions(self, content: str) -> List[str]:
        """Parse @mentions from message content."""
        # Match @username patterns (supports Unicode names)
        pattern = r"@([\w\u4e00-\u9fa5]+)"
        matches = re.findall(pattern, content)
        return matches

    def resolve_mentions(self, mentions: List[str]) -> List[str]:
        """Resolve mention names to cat IDs."""
        if not self._cat_registry:
            return []

        cat_ids = []
        for mention in mentions:
            # Try to find cat by mention pattern
            cat_config = self._cat_registry.get_by_mention(f"@{mention}")
            if cat_config:
                cat_ids.append(cat_config.cat_id)
        return cat_ids

    def get_or_create_thread(self, thread_key: str) -> Optional[str]:
        """Get or create thread ID from connector thread key."""
        if not self._thread_manager:
            # Fallback: use thread_key as thread_id
            return thread_key

        try:
            thread = self._thread_manager.get_or_create(
                external_id=thread_key,
                title=None,  # Could extract from first message
            )
            return thread.id if hasattr(thread, "id") else thread.get("id")
        except Exception:
            return thread_key

    async def _on_inbound_message(self, adapter_name: str, message: InboundMessage) -> None:
        """Handle inbound message from adapter."""
        await self.process_inbound(adapter_name, message)

    async def process_inbound(self, adapter_name: str, message: InboundMessage) -> bool:
        """Process inbound message through pipeline.

        Returns True if message was processed, False if filtered/rejected.
        """
        # 1. Deduplication
        msg_key = self._generate_message_key(adapter_name, message)
        if self._is_duplicate(msg_key):
            return False

        # 2. Group whitelist check
        if self._whitelisted_groups is not None:
            if message.thread_id not in self._whitelisted_groups:
                return False

        # 3. Command interception
        content = message.content.strip()
        if content.startswith("/"):
            parts = content.split()
            command = parts[0]
            if command in self._command_handlers:
                handled = await self._command_handlers[command](message)
                if handled:
                    return True

        # 4. Media processing (download if needed)
        if message.message_type in (MessageType.IMAGE, MessageType.FILE, MessageType.AUDIO):
            if message.file_url and not message.file_url.startswith("/"):
                # Need to download
                adapter = self._adapters.get(adapter_name)
                if adapter and hasattr(adapter, "download_media"):
                    try:
                        success, local_path = await adapter.download_media(message.file_url)
                        if success:
                            message.file_url = local_path
                    except Exception:
                        pass  # Continue without file

        # 5. Binding lookup / Thread creation
        thread_id = self.get_or_create_thread(message.thread_id)
        message.thread_id = thread_id

        # 6. @mention parsing
        mentions = self.parse_mentions(message.content)
        target_cats = self.resolve_mentions(mentions)

        # Also include mentioned_cats from adapter if present
        if message.mentioned_cats:
            target_cats.extend(message.mentioned_cats)

        # Remove duplicates
        target_cats = list(set(target_cats))

        # 7. Store to thread
        if self._thread_manager:
            try:
                await self._add_message_to_thread(thread_id, message)
            except Exception:
                pass  # Continue even if storage fails

        # 8. Broadcast to listeners
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception:
                pass

        # 9. Invoke cat (if mentions or default)
        if self._invocation_queue and target_cats:
            await self._invoke_cats(thread_id, message, target_cats)
        elif self._invocation_queue:
            # No mentions - could invoke default cat or skip
            pass

        return True

    async def _add_message_to_thread(self, thread_id: str, message: InboundMessage) -> None:
        """Add message to thread storage."""
        if not self._thread_manager:
            return

        # Convert to internal message format
        msg_data = {
            "role": "user",
            "content": message.content,
            "metadata": {
                "user_id": message.user_id,
                "user_name": message.user_name,
                "message_type": message.message_type.value,
                "file_url": message.file_url,
            },
        }

        try:
            # Use thread_manager to add message
            if hasattr(self._thread_manager, "add_message"):
                await self._thread_manager.add_message(thread_id, msg_data)
        except Exception:
            pass

    async def _invoke_cats(self, thread_id: str, message: InboundMessage, cat_ids: List[str]) -> None:
        """Queue invocation for target cats."""
        if not self._invocation_queue:
            return

        try:
            if hasattr(self._invocation_queue, "enqueue"):
                self._invocation_queue.enqueue(
                    thread_id=thread_id,
                    user_id=message.user_id,
                    content=message.content,
                    target_cats=cat_ids,
                )
        except Exception:
            pass

    async def send_outbound(
        self,
        thread_key: str,
        message: OutboundMessage,
        adapter_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Send outbound message.

        Args:
            thread_key: Format "adapter:chat_id" or just "chat_id"
            message: Outbound message
            adapter_name: Optional explicit adapter

        Returns:
            (success, error_or_message_id)
        """
        # Parse thread key
        if ":" in thread_key:
            adapter_name, chat_id = thread_key.split(":", 1)
        elif not adapter_name:
            return False, "Cannot determine adapter from thread_key"
        else:
            chat_id = thread_key

        adapter = self._adapters.get(adapter_name)
        if not adapter:
            return False, f"Adapter not found: {adapter_name}"

        try:
            success, result = await adapter.send_message(thread_key, message)
            return success, result
        except Exception as e:
            return False, str(e)

    async def broadcast(
        self,
        message: OutboundMessage,
        thread_keys: List[str],
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Broadcast message to multiple threads."""
        results = {}
        tasks = []

        for key in thread_keys:
            task = self.send_outbound(key, message)
            tasks.append((key, task))

        # Execute all
        for key, task in tasks:
            try:
                success, result = await task
                results[key] = (success, result)
            except Exception as e:
                results[key] = (False, str(e))

        return results

    async def start_all(self) -> None:
        """Start all registered adapters."""
        for name, adapter in self._adapters.items():
            if hasattr(adapter, "start"):
                try:
                    await adapter.start()
                except Exception as e:
                    print(f"Failed to start adapter {name}: {e}")

    async def stop_all(self) -> None:
        """Stop all registered adapters."""
        for name, adapter in self._adapters.items():
            if hasattr(adapter, "stop"):
                try:
                    await adapter.stop()
                except Exception as e:
                    print(f"Failed to stop adapter {name}: {e}")
