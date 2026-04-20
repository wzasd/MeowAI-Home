"""WebSocket endpoint for streaming agent responses."""

import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.collaboration.a2a_controller import A2AController
from src.collaboration.intent_parser import IntentResult, parse_intent
from src.thread.models import Message
from src.web.stream import ConnectionManager
from src.workflow.executor import DAGExecutor
from src.workflow.templates import WorkflowTemplateFactory

router = APIRouter()
manager = ConnectionManager()
log = logging.getLogger(__name__)


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    app = websocket.app
    tm = app.state.thread_manager
    agent_router = app.state.agent_router

    manager.add(thread_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            log.warning("WS RECV thread=%s type=%s", thread_id, data.get("type"))

            if data.get("type") == "send_message":
                await _handle_send_message(
                    websocket, thread_id, data, tm, agent_router, app
                )
            elif data.get("type") == "interactive_action":
                await _handle_interactive_action(websocket, thread_id, data, tm)
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(thread_id, websocket)


async def _handle_interactive_action(websocket, thread_id, data, tm):
    block_id = data.get("block_id", "")
    values = data.get("values", [])

    thread = await tm.get(thread_id)
    if not thread:
        await websocket.send_json({"type": "error", "message": "Thread not found"})
        return

    # Persist to thread metadata
    responses = (
        thread.metadata.get("interactive_responses", []) if thread.metadata else []
    )
    responses.append({"block_id": block_id, "values": values, "timestamp": time.time()})
    if thread.metadata is None:
        thread.metadata = {}
    thread.metadata["interactive_responses"] = responses
    await tm.update_thread(thread)

    await websocket.send_json(
        {
            "type": "interactive_ack",
            "block_id": block_id,
            "values": values,
        }
    )

    # Also broadcast to other connections on the same thread
    await manager.broadcast(
        thread_id,
        {
            "type": "interactive_response",
            "block_id": block_id,
            "values": values,
        },
    )


async def _handle_send_message(websocket, thread_id, data, tm, agent_router, app):
    content = data.get("content", "").strip()
    log.info("WS received send_message: thread=%s content=%.80s", thread_id, content)
    if not content:
        await websocket.send_json({"type": "error", "message": "Empty message"})
        return

    thread = await tm.get(thread_id)
    if not thread:
        await websocket.send_json({"type": "error", "message": "Thread not found"})
        return

    if not thread.project_path:
        await websocket.send_json(
            {"type": "error", "message": "当前 Thread 未绑定项目目录，请先选择项目"}
        )
        return

    if "@" not in content and not content.startswith("/"):
        content = f"@{thread.current_cat_id} {content}"

    agents = agent_router.route_message(content)
    intent = parse_intent(content, len(agents))

    # Force intent override from slash commands (/ideate, /execute)
    force_intent = data.get("forceIntent")
    if force_intent and force_intent in ("ideate", "execute"):
        intent = IntentResult(
            intent=force_intent,
            explicit=True,
            prompt_tags=intent.prompt_tags,
            clean_message=intent.clean_message,
            workflow=intent.workflow,
        )

    # Cancel any active invocations for this thread
    tracker = getattr(app.state, "invocation_tracker", None)
    if tracker:
        tracker.cancel_all(thread_id)

    # Persist user message (with attachments if any)
    attachments = data.get("attachments", []) or []
    metadata = {"attachments": attachments} if attachments else None
    user_msg = Message(role="user", content=intent.clean_message, metadata=metadata)
    thread.add_message("user", intent.clean_message, metadata=metadata)
    await tm.add_message(thread.id, user_msg)

    await websocket.send_json(
        {
            "type": "message_sent",
            "message": {
                "id": user_msg.id,
                "role": "user",
                "content": intent.clean_message,
                "cat_id": None,
                "timestamp": user_msg.timestamp.isoformat() if user_msg.timestamp else None,
                "metadata": metadata,
            },
        }
    )

    await websocket.send_json(
        {
            "type": "intent_mode",
            "mode": intent.workflow or intent.intent,
            "cats": [a["breed_id"] for a in agents],
        }
    )

    try:
        session_chain = getattr(app.state, "session_chain", None)

        dag_executor = None
        template_factory = None
        if intent.workflow:
            agent_registry = getattr(app.state, "agent_registry", None)
            if agent_registry:
                dag_executor = DAGExecutor(
                    agent_registry=agent_registry,
                    session_chain=session_chain,
                    tracker=tracker,
                )
                template_factory = WorkflowTemplateFactory()

        memory_service = getattr(app.state, "memory_service", None)

        # Define broadcast callback for session events
        async def broadcast_session(data: dict):
            await manager.broadcast(thread_id, data)

        mission_store = getattr(app.state, "mission_store", None)
        controller = A2AController(
            agents,
            session_chain=session_chain,
            dag_executor=dag_executor,
            template_factory=template_factory,
            memory_service=memory_service,
            broadcast_callback=broadcast_session,
            mission_store=mission_store,
        )

        if intent.workflow:
            await websocket.send_json(
                {
                    "type": "workflow_start",
                    "workflow": intent.workflow,
                    "cats": [a["breed_id"] for a in agents],
                }
            )

        workflow_cat_ids = []
        log.info(
            "Starting controller.execute: agents=%s intent=%s",
            [a["breed_id"] for a in agents],
            intent.intent,
        )

        # Accumulate streaming content per cat for persistence
        accumulated: dict = {}

        async for response in controller.execute(intent, intent.clean_message, thread):
            log.debug(
                "Yielded response: cat=%s is_final=%s content_len=%d",
                response.cat_id,
                response.is_final,
                len(response.content),
            )
            acc = accumulated.setdefault(
                response.cat_id, {"content": "", "thinking": "", "targetCats": None}
            )

            if response.thinking:
                acc["thinking"] = response.thinking
                await websocket.send_json(
                    {
                        "type": "thinking",
                        "cat_id": response.cat_id,
                        "cat_name": response.cat_name,
                        "content": response.thinking,
                    }
                )

            acc["content"] += response.content
            if response.targetCats is not None:
                acc["targetCats"] = response.targetCats

            # Final response may carry the full parsed content; use it for persistence
            # but do not stream it to the client if they already received the chunks.
            ws_content = response.content
            if response.is_final and response.content:
                acc["content"] = response.content
                ws_content = ""
            elif response.is_final and not acc["content"]:
                # No prior text chunks were streamed; send the final content so the UI
                # has something to display before persistence finishes.
                acc["content"] = response.content

            await websocket.send_json(
                {
                    "type": "cat_response",
                    "cat_id": response.cat_id,
                    "cat_name": response.cat_name,
                    "content": ws_content,
                    "target_cats": response.targetCats,
                }
            )

            if intent.workflow:
                workflow_cat_ids.append(response.cat_id)

            # Only persist final response to database
            if response.is_final:
                msg_metadata = {}
                if response.usage:
                    msg_metadata["usage"] = response.usage
                if response.cli_command:
                    msg_metadata["cli_command"] = response.cli_command
                if response.default_model:
                    msg_metadata["default_model"] = response.default_model
                assistant_msg = Message(
                    role="assistant",
                    content=acc["content"],
                    cat_id=response.cat_id,
                    thinking=acc["thinking"] or None,
                    metadata=msg_metadata if msg_metadata else None,
                )
                thread.add_message("assistant", acc["content"], cat_id=response.cat_id)
                await tm.add_message(thread.id, assistant_msg)

        await tm.update_thread(thread)

        # Auto-record workflow pattern to procedural memory (with dedup)
        if intent.workflow and memory_service and workflow_cat_ids:
            from src.evolution.process_evolution import ProcessEvolution

            pe = ProcessEvolution(memory_service.procedural)
            success = len(workflow_cat_ids) == len(agents)
            pe.store_or_update(
                name=intent.workflow,
                category="workflow",
                steps=workflow_cat_ids,
                trigger_conditions=[intent.clean_message[:100]],
                outcomes={
                    "total_nodes": len(agents),
                    "success": len(workflow_cat_ids),
                    "failed": max(0, len(agents) - len(workflow_cat_ids)),
                },
                success=success,
            )

        if intent.workflow:
            await websocket.send_json({"type": "workflow_done"})
        else:
            await websocket.send_json({"type": "done"})

    except Exception as e:
        log.exception("Error in agent execution: %s", e)
        await websocket.send_json({"type": "error", "message": str(e)})
